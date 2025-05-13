from flask import request, current_app
import requests
import traceback
import sys

from api.dbutils import gcc
from api.user import issue_token, get_user
from api.utils.oauth import OAuthError, verify_id_token

from . import app

# ========================================================================================

"""
tuple[
	{ idx: user_idx, user, shares },	# pro 가입자
	{ mid, name, email },				# 구 페더 가입자
]
"""
def login_user(provider: str, sub: str):
	conn, cursor = gcc()
	cursor.execute('SELECT `idx` FROM `feather_user_auth` WHERE `provider` = %s AND `sub` = %s AND `is_deleted` = 0;', (provider, sub,))
	row = cursor.fetchone()
	
	if row is not None:
		cursor.execute('SELECT `idx` FROM `feather_user_deletion` WHERE `user_idx` = %s AND `canceled_time` IS NULL AND `deleted_time` IS NULL;', (row['idx'],))
		delrow = cursor.fetchone()
		if delrow is not None:
			cursor.execute('UPDATE `feather_user_deletion` SET `canceled_time` = NOW() WHERE `idx` = %s;', (delrow['idx'],))
			conn.commit()
		print(row)
		user, shares = get_user(row['idx'])

		return {
			'idx': row['idx'],
			'user': user,
			'shares': shares,
		}, None 
	else: return None, None
	
	# TODO @kyu 몽고디비 연결 제외
	# 여기부터는 몽고디비에서 찾아서 사용자 반환함
	# iss = None
	# if provider == 'google':
	# 	iss = 'https://accounts.google.com'
	# elif provider == 'apple':
	# 	iss = 'https://appleid.apple.com'
	
	# mdb = get_mongo()
	# if mdb is None:
	# 	return {'error': 'Bad Server'}, 500

	# col_user = mdb['userColl_v1']
	# muser = col_user.find_one({'authKeys': { 'iss': iss, 'authKey': sub }}, {'_id': 1, 'name': 1, 'email': 1})
	# if muser is None:
	# 	return None, None
	
	# return None, {
	# 	'mid': muser['_id'],
	# 	'name': muser['name'],
	# 	'email': muser['email'],
	# }

# google/apple oauth 공통 응답
def finalize_oauth(id_token: str, provider: str, payload: dict):
	user_data, old_info = login_user(provider, payload['sub'])
	if user_data is not None:
		token = issue_token(user_data['idx'])
		if token is None:
			return {'error': 'Bad Server'}, 500

		return {
			'user': user_data['user'],
			'shares': user_data['shares'],
			'token': token,
		}
	
	# TODO @kyu 일단 애플 구현 제외
	# apple 로그인 후 payload 에 email 이 없는 경우가 있음
	if 'email' not in payload:
		print('email not in payload', file=sys.stderr)
		print(id_token, file=sys.stderr)

	# 구 페더 회원가입 정보가 있다면, 해당 회원 정보를 내려주기
	# if old_info is not None:
	# 	return {
	# 		'info': {
	# 			'id_token': id_token,
	# 			'name': old_info['name'],
	# 			'mid': old_info['mid'],
	# 			'email': old_info['email'], # legacy after 250324_0
	# 		}
	# 	}
		
	return {
		'info': {
			'id_token': id_token,
			'name': payload.get('name') or '',
			'email': payload.get('email', ''), # legacy after 250324_0
		}
	}


"""
login 성공시 { user, shares, token }
실패 { info: { id_token, email, name, mid? } }
"""
@app.route('/oauth/google', methods=['POST'])
def oauth_google():
	req = request.get_json()
	code = req.get('code')
	
	# ---------- TEST ----------
	if current_app.debug and code in ('login', 'signup'):
		if code == 'login': # 로그인
			user, shares = get_user(1)

			token = issue_token(1)
			if token is None:
				return {'error': 'Bad Server'}, 500
			
			return {'user': user, 'shares': shares, 'token': token}
		
		else: # 회원가입
			return {'info': {
				'id_token': 'debug',
				# 'email': 'sho@sketchsoft3d.com',
				'name': 'Sho',
				'mid': '1234', # mid 가 있으면 구 페더 사용자, 노트 복구 보여주기
			}}
	# ---------- /TEST ----------

	client_id = current_app.config.get('GOOGLE_OAUTH2_CLIENT_ID')
	client_secret = current_app.config.get('GOOGLE_OAUTH2_CLIENT_SECRET')
	
	if not client_id or not client_secret:
		return {'error': 'Bad Server'}, 500
	
	# 일단 로컬에서 테스트할거니까...
	redirect_uri = 'https://mark.local.softsket.ch' 
	# redirect_uri = 'http://localhost:8000'
	token_uri = 'https://oauth2.googleapis.com/token'
	
	# 왜 앱 로그인은 redirect_uri 를 https://feather.app 로만 줘야할까? 구글 콘솔에서 리다이렉트 유알엘이 이렇게 박혀있나보지뭐;
	# redirect_uri = request.headers.get('Origin', 'https://feather.app') if req.get('gate') or req.get('login') else 'https://feather.app'
	j = requests.post(token_uri, data={
		'grant_type': 'authorization_code',
		'client_id': client_id,
		'client_secret': client_secret,
		'code': code,
		'redirect_uri': redirect_uri,
	}).json()
	if 'error' in j:
		error = ' '.join([j.get('error_description'), j['error']])
		return {'error': error}, 500
	if 'id_token' not in j:
		# error
		return {'error': 'Failed to login (google)'}, 500
	id_token = j['id_token']
	try:
		provider, payload = verify_id_token(id_token, audience=client_id)
		# sub, email, email_verified, name, picture
	except OAuthError as e:
		print(str(e), id_token, file=sys.stderr)
		return {'error': str(e)}, 500
	except:
		traceback.print_exc()
		return {'error': 'Failed to verify id_token'}, 500
	return finalize_oauth(id_token, provider, payload)
	

# TODO @kyu 일단 애플 구현 제외
# @app.route('/oauth/apple', methods=['POST'])
# def oauth_apple():
# 	req = request.get_json()
# 	id_token = req.get('id_token')
	
# 	try:
# 		provider, payload = verify_id_token(id_token, audience='app.feather.pro')
# 		# sub, email, email_verified
# 	except:
# 		traceback.print_exc()
# 		return {'error': 'Failed to verify id_token'}, 500

# 	return finalize_oauth(id_token, provider, payload)
