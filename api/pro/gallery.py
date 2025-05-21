from flask import Flask, request, jsonify, current_app, abort, Response
from werkzeug.utils import secure_filename

import boto3
import os
import base64
import requests
import json

from urllib.parse import urlparse
from api.user import auth_user, get_user
from ulid import ULID
from api.dbutils import gcc

from . import app

# 로컬 개발
if os.getenv("FLASK_ENV") == "development":
	s3 = boto3.client(
		's3',
		aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
		aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
		region_name='ap-northeast-2'
	)
else:
	# EC2에서는 IAM Role로 자동 인증
	s3 = boto3.client('s3', region_name='ap-northeast-2')

@app.route('/publish', methods=['POST'])
@auth_user
def upload_to_gallery(user_idx: int | None):
	BUCKET_NAME = current_app.config.get('BUCKET_NAME')
	S3_REGION = current_app.config.get('AWS_DEFAULT_REGION')

	file = request.files.get('file')
	thumbnail = request.files.get('thumbnail')
	info_raw = request.form.get('info')
	info = json.loads(info_raw) if info_raw else {}

	# info 안에서 필요한 값 꺼내기
	title = info.get('title')
	description = info.get('description')
	tag_list = info.get('tags')
	wip = info.get('wip', False) =='true'
	ratio = info.get('ratio')
	license_str = info.get('license')
	downloadable = True
	print(file, title)
	if license_str in (None, '', 'null', 'undefined'):
		license_value = None
	else:
		license_value = license_str

	if not file or not title:
		return jsonify({'error': 'file and title are required'}), 400

	# ULID 생성
	wid = str(ULID()) 

	# 파일 시그니처 확인
	signature = file.read(4)
	file.seek(0)
	if signature != b'FTHR':
		raise ValueError("wrong file format")

	# S3 경로 기본 prefix
	s3_prefix = f'uploads/users/{user_idx}'

	# 원본 파일 S3 업로드
	filename = secure_filename(file.filename)
	ext = os.path.splitext(filename)[1]
	s3_file_key = f'{s3_prefix}/{wid}{ext}'

	try:
		s3.upload_fileobj(file, BUCKET_NAME, s3_file_key)
	except Exception as e:
		return jsonify({'error': 'Failed to upload main file to S3', 'details': str(e)}), 500

	file_url = f'https://{BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{s3_file_key}'

	thumb_filename = secure_filename(thumbnail.filename)
	thumb_ext = os.path.splitext(thumb_filename)[1]
	s3_thumb_key = f'{s3_prefix}/thumbnails/{wid}{thumb_ext}'
	try:
		s3.upload_fileobj(thumbnail, BUCKET_NAME, s3_thumb_key)
	except Exception as e:
		return jsonify({'error': 'Failed to upload thumbnail to S3', 'details': str(e)}), 500
	
	thumbnail_url = f'https://{BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{s3_thumb_key}'
	# 태그 파싱
	

	conn, cursor = gcc()

	try:
		# 작품 INSERT
		sql = """
			INSERT INTO feather_gallery_works 
			(wid, user_idx, file_url, title, description, wip, downloadable, license, thumbnail, ratio)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
		"""
	
		# 삽입한 작품 ID
		try:
			cursor.execute(sql, (
				wid, user_idx, file_url, title, description,
				wip, downloadable, license_value, thumbnail_url, ratio
			))
			print("INSERT rowcount:", cursor.rowcount)
		except Exception as e:
			print("INSERT 에러:", str(e))
			raise
		cursor.execute("SELECT LAST_INSERT_ID()")
		row = cursor.fetchone()
		work_id = row['LAST_INSERT_ID()']
		# 태그 처리
		for tag_name in tag_list:
			cursor.execute(
				"INSERT INTO gallery_tags (tag) VALUES (%s) ON DUPLICATE KEY UPDATE idx = LAST_INSERT_ID(idx)",
				(tag_name,)
			)
			cursor.execute("SELECT LAST_INSERT_ID()")
			tag_id = cursor.fetchone()['LAST_INSERT_ID()']
				
			cursor.execute(
				"INSERT IGNORE INTO gallery_work_tags (wid, tid) VALUES (%s, %s)",
				(wid, tag_id)
			)

		conn.commit()
	except Exception as e:
		conn.rollback()
		return jsonify({'error': 'Database error', 'details': str(e)}), 500
	finally:
		cursor.close()
		conn.close()

	return jsonify({'message': 'Upload successful', 'wid': wid})


@app.route('/gallery/list', methods=['GET'])
def get_gallery_list():
	try:
		page = int(request.args.get('page', 1))
		size = int(request.args.get('size', 20))
		if page < 1 or size < 1:
			raise ValueError
	except ValueError:
		return jsonify({'error': 'Invalid page or size'}), 400

	offset = (page - 1) * size

	conn, cursor = gcc()

	try:
		# 전체 작품 수
		count_sql = "SELECT COUNT(*) AS total FROM feather_gallery_works WHERE is_deleted = 0;"
		cursor.execute(count_sql)
		total = cursor.fetchone()['total']

		# 작품 리스트 조회
		list_sql = """
		SELECT
			n.wid,
			n.title,
			n.wip,
			n.downloadable,
			n.inserted_time,
			n.thumbnail,
			n.ratio,
			u.handle AS author_handle,
			u.image AS author_image,
			COUNT(DISTINCT l.idx) AS like_count,
			COUNT(DISTINCT d.idx) AS download_count
		FROM feather_gallery_works n
		LEFT JOIN feather_users u ON n.user_idx = u.idx
		LEFT JOIN gallery_work_likes l ON n.wid = l.wid
		LEFT JOIN gallery_work_downloads d ON n.wid = d.wid
		WHERE n.is_deleted = 0 AND u.is_deleted = 0
		GROUP BY n.wid
		ORDER BY n.inserted_time DESC
		LIMIT %s OFFSET %s;
		"""
		cursor.execute(list_sql, (size, offset))
		rows = cursor.fetchall()

		items = []
		for row in rows:
			items.append({
				'wid': row['wid'],
				'title': row['title'],
				'thumbnail': row['thumbnail'],
				'wip': row['wip'],
				'ratio': row['ratio'],
				'downloadable': row['downloadable'],
				'inserted_time': row['inserted_time'].isoformat(),
				'like_count': row['like_count'],
				'download_count': row['download_count'],
				'author': {
					'handle': row['author_handle'],
					'image': row['author_image']
				}
			})              

		return jsonify({
			'page': page,
			'size': size,
			'total': total,
			'items': items
		})

	except Exception as e:
		conn.rollback()
		return jsonify({'error': 'Database error', 'details': str(e)}), 500

	finally:
		cursor.close()
		conn.close()


@app.route('/works/<string:wid>', methods=['DELETE'])
@auth_user
def delete_uploaded_file(wid, user_idx):
	conn, cursor = gcc()

	try:
		cursor.execute("SELECT user_idx FROM feather_gallery_works WHERE wid = %s", (wid,))
		row = cursor.fetchone()

		if not row:
			return jsonify({'error': 'File not found'}), 404
		if row['user_idx'] != user_idx:
			return jsonify({'error': 'Permission denied'}), 403

		# 논리 삭제
		cursor.execute(
			"UPDATE feather_gallery_works SET is_deleted = 1 WHERE wid = %s",
			(wid,)
		)
		conn.commit()

		return jsonify({'message': 'File deleted successfully'})
	
	except Exception as e:
		conn.rollback()
		return jsonify({'error': 'Database error', 'details': str(e)}), 500
	
	finally:
		cursor.close()
		conn.close()

@app.route('/works/<string:wid>', methods=['PUT'])
@auth_user
def update_uploaded_file(wid, user_idx):
	data = request.get_json()

	title = data.get('title')
	description = data.get('description')
	tag_list = data.get('tags', []).split(',')
	wip = data.get('wip', False)
	downloadable = data.get('downloadable', True)
	license_str = data.get('selectedCcOption', None)
	
	conn, cursor = gcc()
	try:
		# 권한 확인
		cursor.execute("SELECT user_idx FROM feather_gallery_works WHERE wid = %s", (wid,))
		row = cursor.fetchone()
		if not row:
			return jsonify({'error': 'File not found'}), 404
		if row['user_idx'] != user_idx:
			return jsonify({'error': 'Permission denied'}), 403

		# 작품 정보 업데이트
		cursor.execute("""
			UPDATE feather_gallery_works
			SET title = %s,
				description = %s,
				wip = %s,
				downloadable = %s,
				license = %s,
				modified_time = CURRENT_TIMESTAMP
			WHERE wid = %s
		""", (title, description, wip, downloadable, license_str, wid))

		# 기존 태그 연결 삭제
		cursor.execute("DELETE FROM gallery_work_tags WHERE wid = %s", (wid,))

		# 태그 재등록
		for tag_name in tag_list:
			cursor.execute(
				"INSERT INTO gallery_tags (tag) VALUES (%s) ON DUPLICATE KEY UPDATE idx = LAST_INSERT_ID(idx)",
				(tag_name,)
			)
			cursor.execute("SELECT LAST_INSERT_ID() AS last_id")
			tag_id = cursor.fetchone()['last_id']			
			cursor.execute(
				"INSERT INTO gallery_work_tags (wid, tid) VALUES (%s, %s)",
				(wid, tag_id)
			)

		conn.commit()
		return jsonify({'message': 'File updated successfully'})

	except Exception as e:
		conn.rollback()
		return jsonify({'error': 'Database error', 'details': str(e)}), 500

	finally:
		cursor.close()
		conn.close()


## 지금 사용중인 api... 굳이 이렇게 해야하나 싶기도 함. 
@app.route('/meta/<string:wid>', methods=['GET'])
@auth_user
def get_gallery_meta_data(wid, user_idx):
	conn, cursor = gcc()

	try:
		# 작품 정보
		cursor.execute("SELECT * FROM feather_gallery_works WHERE wid = %s AND is_deleted = 0", (wid,))
		result = cursor.fetchone()
		if not result or not result["file_url"]:
			return abort(404)

		# 본인 여부
		editable = (user_idx is not None and result["user_idx"] == user_idx)

		# 좋아요 수
		cursor.execute("SELECT COUNT(*) AS count FROM gallery_work_likes WHERE wid = %s", (wid,))
		like_count = cursor.fetchone()["count"]

		# 다운로드 수
		cursor.execute("SELECT COUNT(*) AS count FROM gallery_work_downloads WHERE wid = %s", (wid,))
		download_count = cursor.fetchone()["count"]

		# 사용자 정보
		cursor.execute("SELECT handle, image FROM feather_users WHERE idx = %s", (result["user_idx"],))
		user_data = cursor.fetchone()

		# 태그 목록
		cursor.execute("""
			SELECT t.tag
			FROM gallery_work_tags wt
			JOIN gallery_tags t ON wt.tid = t.idx
			WHERE wt.wid = %s
		""", (wid,))
		tag_rows = cursor.fetchall()
		tags = [row["tag"] for row in tag_rows]

		return jsonify({
			"wid": result["wid"],
			"title": result["title"],
			"description": result["description"],
			"license": result["license"],
			"file_url": result["file_url"],
			"thumbnail_url": result["thumbnail"],
			"tags": tags,
			"wip": result["wip"],
			"downloadable": result["downloadable"],
			"inserted_time": result["inserted_time"].isoformat(),
			"like_count": like_count,
			"download_count": download_count,
			"editable": editable,
			"author" :{
				"handle": user_data["handle"],
				"image": user_data["image"]
			}
		})

	except Exception as e:
		print(e)
		abort(500)
	finally:
		cursor.close()
		conn.close()


@app.route('/work/<string:wid>/like', methods=['POST'])
@auth_user
def toggle_like(wid, user_idx):
	conn, cursor = gcc()

	try:
		# 작품 존재 확인
		cursor.execute("SELECT 1 FROM feather_gallery_works WHERE wid = %s AND is_deleted = 0", (wid,))
		if not cursor.fetchone():
			return jsonify({'error': '작품이 존재하지 않습니다.'}), 404

		# 현재 좋아요 상태 확인
		cursor.execute("""
			SELECT idx FROM gallery_work_likes
			WHERE user_idx = %s AND wid = %s
		""", (user_idx, wid))
		like = cursor.fetchone()

		if like:
			# 좋아요 취소
			cursor.execute("DELETE FROM gallery_work_likes WHERE user_idx = %s AND wid = %s", (user_idx, wid))
			action = 'unliked'
			liked_by_me = False
		else:
			# 좋아요 추가
			cursor.execute("""
				INSERT INTO gallery_work_likes (user_idx, wid)
				VALUES (%s, %s)
			""", (user_idx, wid))
			action = 'liked'
			liked_by_me = True

		# 총 좋아요 수 확인
		cursor.execute("SELECT COUNT(*) AS like_count FROM gallery_work_likes WHERE wid = %s", (wid,))
		like_count = cursor.fetchone()['like_count']

		conn.commit()

		return jsonify({
			'message': f'Successfully {action}',
			'action': action,
			'like_count': like_count,
			'liked_by_me': liked_by_me
		})

	except Exception as e:
		conn.rollback()
		return jsonify({'error': 'Like 처리 실패', 'details': str(e)}), 500
	finally:
		cursor.close()
		conn.close()

@app.route('/work/<string:wid>/like-status', methods=['GET'])
@auth_user
def get_like_status(wid, user_idx):
	conn, cursor = gcc()
	try:
		cursor.execute("""
			SELECT 1 FROM gallery_work_likes
			WHERE user_idx = %s AND wid = %s
		""", (user_idx, wid))
		liked = cursor.fetchone() is not None
		return jsonify({'liked_by_me': liked})
	finally:
		cursor.close()
		conn.close()

# TODO 나중엔 서버에서 내려주는 방향일지도...? 지금 상태는 그냥 언제든 s3파일을 받을 수 있는 구조로 가고있음. 꼭 서버에서 검증해서 내려주고, 
# 아니면 downloadable false인 애들 presigned로 내려줄 것. 그럼 공개 범위를 다르게 하는 파일로 해야하는데 괜찮나?
@app.route('/work/<string:wid>/download', methods=['GET'])
@auth_user
def get_download_url(wid, user_idx):
	conn, cursor = gcc()
	try:
		cursor.execute("""
			SELECT file_url, downloadable, user_idx
			FROM feather_gallery_works
			WHERE wid = %s AND is_deleted = 0
		""", (wid,))

		result = cursor.fetchone()

		if not result:
			return jsonify({'error': '작품이 존재하지 않습니다.'}), 404
		if not result['downloadable'] and result['user_idx'] != user_idx:
			return jsonify({'error': '다운로드 권한이 없습니다.'}), 403

		cursor.execute("""
			INSERT INTO gallery_work_downloads (
				user_idx, post_ulid, ip_address, user_agent, inserted_time
			) VALUES (%s, %s, %s, %s, NOW())
		""", (
			user_idx,
			wid,
			request.remote_addr,
			request.headers.get('User-Agent'),
		))

		conn.commit()
		return jsonify({
			'download_url': result['file_url']
		})

	except Exception as e:
		conn.rollback()
		return jsonify({'error': '다운로드 기록 실패', 'details': str(e)}), 500
	finally:
		cursor.close()
		conn.close()

@app.route('/users/<string:user_handle>/likes', methods=['GET'])
def get_liked_gallery_list(user_handle):
	try:
		page = int(request.args.get('page', 1))
		size = int(request.args.get('size', 20))
		if page < 1 or size < 1:
			raise ValueError
	except ValueError:
		return jsonify({'error': 'Invalid page or size'}), 400

	offset = (page - 1) * size

	conn, cursor = gcc()

	try:
		# handle로 user_idx 조회
		cursor.execute("SELECT idx FROM feather_users WHERE handle = %s AND is_deleted = 0", (user_handle,))
		
		user_row = cursor.fetchone()
		if not user_row:
			return jsonify({'error': 'User not found'}), 404

		user_idx = user_row['idx']

		# 전체 좋아요 수 (삭제된 작품 제외)
		count_sql = """
		SELECT COUNT(*) AS total
		FROM gallery_work_likes gl
		JOIN feather_gallery_works fw ON gl.wid = fw.wid
		WHERE gl.user_idx = %s AND fw.is_deleted = 0;
		"""
		cursor.execute(count_sql, (user_idx,))
		total = cursor.fetchone()['total']

		# 좋아요한 작품 리스트
		list_sql = """
		SELECT
			fw.wid,
			fw.title,
			fw.wip,
			fw.downloadable,
			fw.inserted_time,
			fw.thumbnail,
			fw.ratio,
			u.handle AS author_handle,
			u.image AS author_image,
			COUNT(DISTINCT l.idx) AS like_count,
			COUNT(DISTINCT d.idx) AS download_count
		FROM gallery_work_likes gl
		JOIN feather_gallery_works fw ON gl.wid = fw.wid
		LEFT JOIN feather_users u ON fw.user_idx = u.idx
		LEFT JOIN gallery_work_likes l ON fw.wid = l.wid
		LEFT JOIN gallery_work_downloads d ON fw.wid = d.wid
		WHERE gl.user_idx = %s AND fw.is_deleted = 0 AND u.is_deleted = 0
		GROUP BY fw.wid
		ORDER BY fw.inserted_time DESC
		LIMIT %s OFFSET %s;
		"""
		cursor.execute(list_sql, (user_idx, size, offset))
		rows = cursor.fetchall()

		items = []
		for row in rows:
			items.append({
				'wid': row['wid'],
				'title': row['title'],
				'thumbnail': row['thumbnail'],
				'wip': row['wip'],
				'ratio': row['ratio'],
				'downloadable': row['downloadable'],
				'inserted_time': row['inserted_time'].isoformat(),
				'like_count': row['like_count'],
				'download_count': row['download_count'],
				'author': {
					'handle': row['author_handle'],
					'image': row['author_image']
				}
			})

		return jsonify({
			'page': page,
			'size': size,
			'total': total,
			'items': items
		})

	except Exception as e:
		conn.rollback()
		return jsonify({'error': 'Database error', 'details': str(e)}), 500

	finally:
		cursor.close()
		conn.close()


@app.route('/users/<string:user_handle>/stats', methods=['GET'])
def get_user_stats(user_handle):
	conn, cursor = gcc()

	try:
		# 1. handle로 user_idx 조회
		cursor.execute("SELECT idx FROM feather_users WHERE handle = %s AND is_deleted = 0", (user_handle,))
		
		user_row = cursor.fetchone()
		if not user_row:
			return jsonify({'error': 'User not found'}), 404

		user_idx = user_row['idx']

		sql = """
		SELECT
		  u.user_idx,

		  -- 내가 올린 작품 수
		  (SELECT COUNT(*) 
		   FROM feather_gallery_works fw 
		   WHERE fw.user_idx = u.user_idx AND fw.is_deleted = 0
		  ) AS total_works,

		  -- 내 작품이 받은 좋아요 수
		  (SELECT COUNT(*) 
		   FROM gallery_work_likes gl 
		   JOIN feather_gallery_works fw2 ON gl.wid = fw2.wid 
		   WHERE fw2.user_idx = u.user_idx AND fw2.is_deleted = 0
		  ) AS total_likes,

		  -- 내 작품이 받은 다운로드 수
		  (SELECT COUNT(*) 
		   FROM gallery_work_downloads gd 
		   JOIN feather_gallery_works fw3 ON gd.wid = fw3.wid 
		   WHERE fw3.user_idx = u.user_idx AND fw3.is_deleted = 0
		  ) AS total_downloads,

		  -- 내가 좋아요 누른 작품 수
		  (SELECT COUNT(*) 
		   FROM gallery_work_likes gl2
		   JOIN feather_gallery_works fw4 ON gl2.wid = fw4.wid
		   WHERE gl2.user_idx = u.user_idx AND fw4.is_deleted = 0
		  ) AS liked_works

		FROM (SELECT %s AS user_idx) u;
		"""
		cursor.execute(sql, (user_idx,))
		row = cursor.fetchone()
		
		if not row:
			return jsonify({'error': 'User not found'}), 404

		result = {
			'user_idx': row['user_idx'],
			'total_works': row['total_works'],
			'total_likes': row['total_likes'],
			'total_downloads': row['total_downloads'],
			'liked_works': row['liked_works']
		}

		return jsonify(result)

	except Exception as e:
		conn.rollback()
		return jsonify({'error': 'Database error', 'details': str(e)}), 500

	finally:
		cursor.close()
		conn.close()

@app.route('/users/<string:user_handle>/works', methods=['GET'])
def get_user_works(user_handle):
	try:
		page = int(request.args.get('page', 1))
		size = int(request.args.get('size', 20))
		if page < 1 or size < 1:
			raise ValueError
	except ValueError:
		return jsonify({'error': 'Invalid page or size'}), 400

	offset = (page - 1) * size
	conn, cursor = gcc()
	
	try:
		# handle로 user_idx 조회
		cursor.execute("SELECT idx FROM feather_users WHERE handle = %s AND is_deleted = 0", (user_handle,))
		
		user_row = cursor.fetchone()
		if not user_row:
			return jsonify({'error': 'User not found'}), 404

		user_idx = user_row['idx']
		print('idx', user_idx)
		# 전체 작품 수
		count_sql = """
		SELECT COUNT(*) AS total
		FROM feather_gallery_works
		WHERE is_deleted = 0 AND user_idx = %s;
		"""
		cursor.execute(count_sql, (user_idx,))
		total = cursor.fetchone()['total']

		# 작품 리스트 조회
		list_sql = """
		SELECT
			n.wid,
			n.title,
			n.wip,
			n.downloadable,
			n.inserted_time,
			n.thumbnail,
			n.ratio,
			u.handle AS author_handle,
			u.image AS author_image,
			COUNT(DISTINCT l.idx) AS like_count,
			COUNT(DISTINCT d.idx) AS download_count
		FROM feather_gallery_works n
		LEFT JOIN feather_users u ON n.user_idx = u.idx
		LEFT JOIN gallery_work_likes l ON n.wid = l.wid
		LEFT JOIN gallery_work_downloads d ON n.wid = d.wid
		WHERE n.is_deleted = 0 AND n.user_idx = %s AND u.is_deleted = 0
		GROUP BY n.wid
		ORDER BY n.inserted_time DESC
		LIMIT %s OFFSET %s;
		"""
		cursor.execute(list_sql, (user_idx, size, offset))
		rows = cursor.fetchall()

		items = []
		for row in rows:
			items.append({
				'wid': row['wid'],
				'title': row['title'],
				'thumbnail': row['thumbnail'],
				'wip': row['wip'],
				'ratio': row['ratio'],
				'downloadable': row['downloadable'],
				'inserted_time': row['inserted_time'].isoformat(),
				'like_count': row['like_count'],
				'download_count': row['download_count'],
				'author': {
					'handle': row['author_handle'],
					'image': row['author_image']
				}
			})

		return jsonify({
			'page': page,
			'size': size,
			'total': total,
			'items': items
		})

	except Exception as e:
		conn.rollback()
		return jsonify({'error': 'Database error', 'details': str(e)}), 500

	finally:
		cursor.close()
		conn.close()


def is_bot(user_agent):
	bot_keywords = ['bot', 'crawl', 'spider', 'preview', 'slurp']
	print(user_agent.lower())
	return any(kw in user_agent.lower() for kw in bot_keywords)

@app.route('/log-view', methods=['POST'])
def log_view():
	data = request.get_json()

	wid = data.get('wid')	
	session_id = data.get('session_id')
	referrer = request.headers.get('Referer')
	ip = request.headers.get('X-Forwarded-For', request.remote_addr)
	user_agent = request.headers.get('User-Agent', '')
	handle = data.get('handle')  # optional

	if not wid or is_bot(user_agent):
		print('bot')
		return '', 204  # 필수 정보 없거나 봇이면 무시

	try:
		conn, cursor = gcc()

		# 중복 체크: 1시간 내 같은 IP + UA + wid
		# 나주에 id -> idx 로
		cursor.execute("""
			SELECT idx FROM gallery_work_viewcount
			WHERE ip_address = %s AND wid = %s AND user_agent = %s
			AND viewed_at > NOW() - INTERVAL 1 HOUR
			LIMIT 1
		""", (ip, wid, user_agent))
		
		if cursor.fetchone():
			return '', 204  # 이미 기록된 경우
		

		# 조회 기록 INSERT
		cursor.execute("""
			INSERT INTO gallery_work_viewcount (ip_address, user_agent, referrer, session_id, handle, wid)
			VALUES (%s, %s, %s, %s, %s, %s)
		""", (ip, user_agent, referrer, session_id, handle, wid))

		conn.commit()
		return '', 200

	except Exception as e:
		conn.rollback()
		return jsonify({'error': '조회 기록 실패', 'details': str(e)}), 500
	finally:
		cursor.close()
		conn.close()
