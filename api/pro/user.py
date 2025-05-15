from flask import request, current_app, jsonify
from werkzeug.utils import secure_filename
import traceback
import json
import random
import boto3
import os

from api.dbutils import gcc
from api.user import auth_user, issue_token, get_user, parse_token, get_user_by_handle
from api.utils.oauth import verify_id_token

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

# handle 사용 여부 확인
# 본인 handle 체크를 위해서 user_idx 를 반환함
# -1 은 금지 리스트, 0 은 사용가능
def check_handle_availability(handle: str, cursor = None) -> int:
	if len(handle) < 3 or len(handle) > 30: return -1

	if cursor is None:
		conn, cursor = gcc()
	
	cursor.execute('SELECT `handle` FROM `feather_handle_denylist` WHERE `handle` = %s;', (handle,))
	row = cursor.fetchone()
	if row is not None: return -1

	cursor.execute('SELECT `idx` FROM `feather_users` WHERE `handle` = %s FOR UPDATE;', (handle,))
	row = cursor.fetchone()
	if row is not None: return row['idx']

	return 0


# handle 사용 가능 여부 확인
@app.route('/user/handle/verify')
@auth_user
def user_handle_verify(user_idx: int | None):
	handle = request.values.get('handle')
	handle_user_idx = check_handle_availability(handle)

	return {
		'available': user_idx == handle_user_idx or handle_user_idx == 0
	}

# 회원가입 (이름/핸들만 입력하고 설문조사 전에 호출됨)
@app.route('/user/signup', methods=['POST'])
def user_signup():
	req = request.get_json()

	id_token = req.get('id_token')
	agree_email = req.get('agree_email', False)
	agree_push = req.get('agree_push', False)

	name = req.get('name') or '' # legacy if name is exists
	handle = req.get('handle') # legacy

	if not id_token: # not name or not handle
		return {'error': 'Bad Request'}, 400
	print(current_app.debug, id_token)

	# ---------- TEST ----------
	if current_app.debug and id_token == 'debug':
		print('return??')
		token = issue_token(1)
		if token is None:
			return {'error': 'Bad Server'}, 500
		
		user, shares = get_user(1)
		return {
			'user': user,
			'shares': shares,
			'token': token,
		}
	# ---------- /TEST ----------


	# verify id_token
	provider, payload = verify_id_token(id_token)

	conn, cursor = gcc()
	cursor.execute('SELECT `user_idx` FROM `feather_user_auth` WHERE `provider` = %s AND `sub` = %s AND `is_deleted` = 0;', (provider, payload['sub'],))
	row = cursor.fetchone()
	print(row)

	if row is not None:
		return {'error': 'alreadySignedUp'}, 400
	print(row)
	# verify handle
	if handle is not None:
		# legacy
		if check_handle_availability(handle, cursor=cursor) != 0:
			return {'error': 'handleUnavailable'}, 400
	else:
		email = payload.get('email') or ''
		handle = email[:email.find('@')]

		for i in range(50):
			result = check_handle_availability(handle, cursor=cursor)
			if result == 0: break
			
			handle = 'user_' + ''.join([random.choice('0123456789') for _ in range(5)])
		else:
			# 50번 동안 핸들을 정하지 못한 경우
			return {'error': 'handleUnavailable'}, 500
			
	# TODO kyu 우선 몽고디비는 aut
	# find old user id
	# mid = None
	# try:
	# 	iss = None
	# 	if provider == 'google':
	# 		iss = 'https://accounts.google.com'
	# 	elif provider == 'apple':
	# 		iss = 'https://appleid.apple.com'
		
	# 	# mdb = get_mongo()
	# 	# if mdb is None:
	# 	# 	return {'error': 'Bad Server'}, 500
		
	# 	# col_user = mdb['userColl_v1']
	# 	# user = col_user.find_one({'authKeys': { 'iss': iss, 'authKey': payload['sub'] }}, {'_id': 1})

	# 	# if user is not None: mid = user['_id']
	# except Exception as e:
	# 	traceback.print_exc()

	# insert
	cursor.execute('''
		INSERT INTO `feather_users`
		(`mid`, `handle`, `name`, `email`, `image`, `agree_email`, `agree_push`, `is_deleted`)
		VALUES (NULL, %s, %s, %s, NULL, %s, %s, 0);
		''', (
		handle,
		name or handle,
		payload.get('email') or '',
		agree_email,
		agree_push,
	))
	user_idx = cursor.lastrowid
	
	cursor.execute('INSERT INTO `feather_user_auth` VALUES (NULL, %s, %s, %s, NOW(), 0);', (
		user_idx, provider, payload['sub'],
	))
	conn.commit()

	# 다시 질의
	user, shares = get_user(user_idx, False)
	if user is None:
		return {'error': 'serverError'}, 500

	token = issue_token(user_idx)
	if token is None:
		return {'error': 'Bad Server'}, 500
	
	return {
		'user': user,
		'shares': shares,
		'token': token,
	}

# 회원가입 직후 설문조사 등록
@app.route('/user/signup/survey', methods=['POST'])
@auth_user
def user_survey(user_idx: int | None):
	print(user_idx)
	if user_idx is None:
		return {'error': 'Unauthorized'}, 401
	
	# ---------- TEST ----------
	if current_app.debug and user_idx == 1:
		return {'error': None}
	# ---------- /TEST ----------

	req = request.get_json()
	
	conn, cursor = gcc()
	cursor.execute('INSERT INTO `feather_user_survey` VALUES (NULL, %s, %s, %s, %s, NOW());', (
		user_idx, req.get('referral', ''), req.get('occupation', ''), json.dumps(req.get('fields', []), ensure_ascii=False),
	))
	conn.commit()

	return {'error': None}


# frontend init 시 세션 정보 확인 용
@app.route('/user')
@auth_user
def user_get(user_idx: int | None):
	print('user_get')
	user, shares = None, []
	if user_idx is not None:
		user, shares = get_user(user_idx)
	
	return {'user': user, 'shares': shares}


# 본인 정보 수정
@app.route('/user', methods=['PATCH'])
@auth_user
def user_patch(user_idx: int | None):
	if user_idx is None:
		return {'error': 'Unauthorized'}, 401
	
	user, _ = get_user(user_idx, share=False)
	if user is None:
		return {'error': 'Unauthorized'}, 401
	
	is_multipart = request.content_type.startswith('multipart/form-data')
	req = request.form if is_multipart else request.get_json()

	# feather_users
	query_set, query_val = [], []

	if is_multipart and 'file' in request.files:
		image_file = request.files['file']
		if image_file and image_file.filename != '':
			filename = secure_filename(image_file.filename)
			
			BUCKET_NAME = current_app.config.get('BUCKET_NAME')
			S3_REGION = current_app.config.get('AWS_DEFAULT_REGION')

			s3_prefix = f'userThumbnail'

			# 원본 파일 S3 업로드
			ext = os.path.splitext(filename)[1]
			s3_file_key = f'{s3_prefix}/{user_idx}{ext}'
			file_url = f'https://{BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{s3_file_key}'

			s3.upload_fileobj(image_file, BUCKET_NAME, s3_file_key)
			
			query_set += ['`image` = %s']
			query_val += [file_url]
			print(query_set, query_val)

	agree = req.get('agree')
	if agree is not None and (agree.get('email') != user['agree']['email'] or agree.get('push') != user['agree']['push']):
		new_agree = agree.get('email') or agree.get('push')
		old_agree = user['agree']['email'] or user['agree']['push']

		query_set += ['`agree_email` = %s', '`agree_push` = %s']
		query_val += [agree.get('email'), agree.get('push')]
		if new_agree != old_agree:
			query_set.append('`agree_time` = NOW()')
	
	keys = ['name', 'handle']
	for key in keys:
		val = req.get(key)
		if val is None: continue

		if val != user[key]:
			query_set.append(f'`{key}` = %s')
			query_val.append(val)

	# feather_user_about
	about_query_set, about_query_val = [], []
	keys = ['about', 'link_home', 'link_instagram', 'link_x', 'link_tiktok']
	for key in keys:
		val = req.get(key)
		if val is None: continue

		orig_val = user['link'][key[5:]] if key.startswith('link_') else user[key]
		if val != orig_val:
			about_query_set.append(f'`{key}` = %s')
			about_query_val.append(val)

	# update
	if len(query_set) == 0 and len(about_query_set) == 0:
		user, _ = get_user(user_idx, False)
		return {'user': user}
	
	conn, cursor = gcc()
	if len(query_set) > 0:
		query_val.append(user_idx)
		cursor.execute(f'UPDATE `feather_users` SET ' + ', '.join(query_set) + ' WHERE `idx` = %s;', query_val)
	
	if len(about_query_set) > 0:
		cursor.execute('SELECT `idx` FROM `feather_user_about` WHERE `idx` = %s;', (user_idx,))
		row = cursor.fetchone()
		if row is None:
			about_query_val = [req.get(key, '') for key in ['about', 'link_home', 'link_instagram', 'link_x', 'link_tiktok']]
			about_query_val.insert(0, user_idx)

			cursor.execute('''INSERT INTO `feather_user_about`
				(`idx`, `about`, `link_home`, `link_instagram`, `link_x`, `link_tiktok`)
				VALUES (%s, %s, %s, %s, %s, %s);''', about_query_val)
		else:
			about_query_val.append(user_idx)
			cursor.execute(f'UPDATE `feather_user_about` SET ' + ', '.join(about_query_set) + ' WHERE `idx` = %s;', about_query_val)
	
	conn.commit()

	user, _ = get_user(user_idx, False)
	return {'user': user}

# 계정 삭제
@app.route('/user', methods=['DELETE'])
@auth_user
def user_delete(user_idx: int | None):
	if user_idx is None:
		return {'error': 'Unauthorized'}, 401
	
	conn, cursor = gcc()
	cursor.execute('INSERT INTO `feather_user_deletion` VALUES (NULL, %s, NOW(), NULL, NOW());', (user_idx,))
	cursor.execute('UPDATE `feather_users` SET `is_deleted` = 1 WHERE `idx` = %s;', (user_idx,))
	cursor.execute('UPDATE `feather_user_token` SET `is_deleted` = 1 WHERE `user_idx` = %s;', (user_idx,))
	cursor.execute('UPDATE `feather_user_auth` SET `is_deleted` = 1 WHERE `user_idx` = %s;', (user_idx,))
	conn.commit()

	return {'error': None}

# 로그아웃, 토큰 만료
@app.route('/user/token', methods=['DELETE'])
@auth_user
def user_token_delete(user_idx: int | None):
	if user_idx is None:
		return {'error': 'Unauthorized'}, 401
	
	_, payload = parse_token()

	conn, cursor = gcc()
	cursor.execute('UPDATE `feather_user_token` SET `is_deleted` = 1 WHERE `user_idx` = %s AND `iat` = %s AND `is_deleted` = 0;', (user_idx, payload['iat'],))
	conn.commit()

	return {'error': None}


@app.route('/user/restore/note')
def dev_restore_note(device_idx: int | None):
	remote_addr = request.headers.get('X-Forwarded-For') or request.remote_addr
	if remote_addr == '127.0.0.1': pass
	elif device_idx is None: return {'error': 'Unauthorized'}, 401


@app.route('/users/<handle>', methods=['GET'])
def get_user_by_handle_route(handle):
	user = get_user_by_handle(handle)
	if user is None:
		return jsonify({'error': 'User not found'}), 404
	return jsonify({'user': user})