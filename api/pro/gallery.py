from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

import boto3
import os
import base64

from api.user import auth_user, get_user
from ulid import ULID
from api.dbutils import gcc

from . import app


if os.getenv("FLASK_ENV") == "development":
    # 로컬 개발 (환경변수 또는 aws configure 사용)
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name='ap-northeast-2'
    )
else:
    # EC2에서는 IAM Role로 자동 인증
    s3 = boto3.client('s3', region_name='ap-northeast-2')

BUCKET_NAME = app.config.get('BUCKET_NAME')
S3_REGION = app.config.get('AWS_DEFAULT_REGION')

@app.route('/upload', methods=['POST'])
@auth_user
def upload_to_gallery(user_idx: int | None):

    file = request.files.get('file')
    thumbnail = request.files.get('thumbnail')
    # title = request.form.get('title')
    # description = request.form.get('description')
    # tag = request.form.get('tag')
    # wip = request.form.get('wip') == 'true'
    # downloadable = request.form.get('downloadable') == 'true'
    # license = request.form.get('license')

    title = 'a'
    description = 'b'
    tag = 'c'
    wip = False
    downloadable = False
    license = None
    print('savvvvve')
    if not file or not title:
        return jsonify({'error': 'file and title are required'}), 400

    # ULID 생성
    file_ulid = str(ULID()) 

    # 파일 확장자 추출
    original_filename = secure_filename(file.filename)
    ext = os.path.splitext(original_filename)[1]  # ex: '.jpg'
    if not ext:
        ext = '.bin'  # 기본 확장자 없을 때 fallback

    # 파일 업로드 (S3)
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1]
    s3_key = f'uploads/{file_ulid}{ext}'

    try:
        s3.upload_fileobj(file, BUCKET_NAME, s3_key)
    except Exception as e:
        return jsonify({'error': 'Failed to upload to S3', 'details': str(e)}), 500

    file_url = f'https://{BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{s3_key}'

    # DB 저장
    conn, cursor = gcc()

    # DB 저장
    try:
        sql = """
            INSERT INTO feather_gallery_notes 
            (ulid, user_idx, file_url, title, description, tag, wip, downloadable, license, thumbnail)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        thumbnail_data = thumbnail.read() if thumbnail else None
        cursor.execute(sql, (
            file_ulid, user_idx, file_url, title, description, tag, # 유저아이디 그냥 박음
            wip, downloadable, license, thumbnail_data
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify({'message': 'Upload successful', 'file_ulid': str(file_ulid)})



@app.route('/gallery/list', methods=['get'])
def get_gallery_list():
    # 페이지, 사이즈 파라미터 파싱
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
        # 총 개수 조회
        count_sql = "SELECT COUNT(*) as total FROM feather_gallery_notes;"
        cursor.execute(count_sql)
        total = cursor.fetchone()['total']

        # 리스트 조회
        list_sql = """
        SELECT ulid, title, wip, downloadable, created_at, thumbnail
        FROM feather_gallery_notes
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s;
        """
        cursor.execute(list_sql, (size, offset))
        rows = cursor.fetchall()

        items = []
        for row in rows:
            thumbnail_data = row['thumbnail']

            thumbnail_base64 = None
            if thumbnail_data:
                thumbnail_base64 = base64.b64encode(thumbnail_data).decode('utf-8')

            items.append({
                'file_ulid': row['ulid'],
                'title': row['title'],
                'thumbnail': thumbnail_base64,  # base64 인코딩한 것 넣기
                'wip': row['wip'],
                'downloadable': row['downloadable'],
                'created_at': row['created_at'].isoformat()
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
