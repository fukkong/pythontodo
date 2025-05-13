from flask import Flask, request, jsonify, current_app, abort, Response
from werkzeug.utils import secure_filename

import boto3
import os
import base64
import requests

from urllib.parse import urlparse
from api.user import auth_user, get_user
from ulid import ULID
from api.dbutils import gcc
import re 

from . import app


## 0-depth 댓글 조회
@app.route('/works/<wid>/comments', methods=['GET'])
def get_comments(wid):
	limit = int(request.args.get('limit', 20))
	offset = int(request.args.get('offset', 0))

	_, cursor = gcc()

	# 댓글 + 사용자 정보 조회 사용자 섬네일 주소는 변수명 정해야함. profile_url ?
	cursor.execute("""
		SELECT 
			c.idx, c.content, c.is_deleted, c.inserted_time,
			u.handle, u.image 
		FROM gallery_comments c
		JOIN feather_users u ON c.user_idx = u.idx
		WHERE c.wid = %s AND c.parent_id IS NULL AND c.is_deleted = FALSE
		ORDER BY c.inserted_time ASC
		LIMIT %s OFFSET %s
	""", (wid, limit, offset))

	comments = cursor.fetchall()
	comment_ids = [row['idx'] for row in comments]

	# 대댓글 숫자 조회
	replies_count = {}
	if comment_ids:
		format_strings = ','.join(['%s'] * len(comment_ids))
		cursor.execute(f"""
			SELECT parent_id, COUNT(*) as cnt
			FROM gallery_comments
			WHERE parent_id IN ({format_strings}) AND is_deleted = FALSE
			GROUP BY parent_id
		""", comment_ids)
		for row in cursor.fetchall():
			replies_count[row['parent_id']] = row['cnt']

	# wrap up
	result = []
	for row in comments:
		result.append({
			'idx': row['idx'],
			'user': {
				'handle': row['handle'],
				'image': row['image']
			},
			'content': None if row['is_deleted'] else row['content'],
			'is_deleted': row['is_deleted'],
			'inserted_time': row['inserted_time'].isoformat(),
			'replies_count': replies_count.get(row['idx'], 0)
		})

	return jsonify(result)

# 1-depth 댓글 조회
@app.route('/comments/<int:comment_id>/replies', methods=['GET'])
def get_replies(comment_id):
	limit = int(request.args.get('limit', 20))
	offset = int(request.args.get('offset', 0))

	_, cursor = gcc()

	cursor.execute("""
		SELECT 
			c.idx, c.content, c.is_deleted, c.inserted_time, c.parent_id,
			u.handle, u.image
		FROM gallery_comments c
		JOIN feather_users u ON c.user_idx = u.idx
		WHERE c.parent_id = %s
		ORDER BY c.inserted_time ASC
		LIMIT %s OFFSET %s
	""", (comment_id, limit, offset))

	replies = cursor.fetchall()

	result = []
	for row in replies:
		result.append({
			'idx': row['idx'],
			'user': {
				'handle': row['handle'],
				'image': row['image']
			},
			'content': None if row['is_deleted'] else row['content'],
			'is_deleted': row['is_deleted'],
			'parent_id': row['parent_id'],
			'inserted_time': row['inserted_time'].isoformat()
		})

	return jsonify(result)


## 댓글 추가
@app.route('/works/<wid>/comments', methods=['POST'])
@auth_user
def post_comment(wid, user_idx):
	data = request.get_json()
	
	# TODO 추가적인 검증 및 욕설 필터 필요
	content = data.get('content', '').strip()
	parent_id = data.get('parent_id')

	if not content:
		return jsonify({"error": "내용을 입력해주세요."}), 400

	conn, cursor = gcc()

	try:
		# parent idx 정리
		actual_parent_id = None

		if parent_id:
			cursor.execute("""
				SELECT idx, user_idx, parent_id
				FROM gallery_comments
				WHERE idx = %s
			""", (parent_id,))
			parent_row = cursor.fetchone()

			if not parent_row:
				return jsonify({"error": "존재하지 않는 댓글입니다."}), 404

			# 3depth 방지: 대댓글의 부모를 최상위로 치환
			if parent_row['parent_id'] is not None:
				actual_parent_id = parent_row['parent_id']
			else:
				actual_parent_id = parent_row['idx']

		# 저장
		cursor.execute("""
			INSERT INTO gallery_comments (wid, parent_id, user_idx, content)
			VALUES (%s, %s, %s, %s)
		""", (wid, actual_parent_id, user_idx, content))
		comment_id = cursor.lastrowid

		# 저장된 댓글 불러오기
		cursor.execute("""
			SELECT c.idx, c.content, c.inserted_time, c.parent_id,
				u.handle, u.image
			FROM gallery_comments c
			JOIN feather_users u ON c.user_idx = u.idx
			WHERE c.idx = %s
		""", (comment_id,))
		comment_row = cursor.fetchone()

		conn.commit()

		return jsonify({
			"idx": comment_row["idx"],
			"content": comment_row["content"],
			"inserted_time": comment_row["inserted_time"].isoformat(),
			"parent_id": comment_row["parent_id"],
			"user": {
				"handle": comment_row["handle"],
				"image": comment_row["image"]
			}
		}), 201

	except Exception as e:
		conn.rollback()
		return jsonify({"error": str(e)}), 500

## 댓글 삭제
@app.route('/comments/<int:comment_id>', methods=['DELETE'])
@auth_user
def delete_comment(comment_id, user_idx):
	conn, cursor = gcc()
	
	cursor.execute("""
		UPDATE gallery_comments
		SET is_deleted = TRUE
		WHERE idx = %s AND user_idx = %s
	""", (comment_id, user_idx))

	if cursor.rowcount == 0:
		return jsonify({"error": "삭제 권한이 없습니다."}), 403

	conn.commit()
	return jsonify({"success": True, "idx": comment_id})

## work의 is_deleted 제외 총 댓글 수 조회
@app.route('/works/<wid>/comments/count', methods=['GET'])
def get_comment_count(wid):
	_, cursor = gcc()

	cursor.execute("""
		SELECT COUNT(*) AS count
		FROM gallery_comments
		WHERE wid = %s AND is_deleted = FALSE
	""", (wid,))
	row = cursor.fetchone()

	return jsonify({"count": row['count']})
