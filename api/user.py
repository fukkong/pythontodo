from flask import request, current_app
from sqids import Sqids
import datetime
import jwt

from api.dbutils import gcc, group_column, bool_columns

from functools import wraps
def auth_user(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		kwargs['user_idx'] = None

		try:
			user_idx, payload = parse_token()

			if user_idx is not None:
				conn, cursor = gcc()
				cursor.execute('''SELECT
					T.`idx`
				FROM `feather_user_token` T
				WHERE T.`user_idx` = %s AND T.`iat` = %s AND T.`is_deleted` = 0;''', (
					user_idx, payload['iat'],
				))

				result = cursor.fetchone()
				print(result)

				if result is not None:
					kwargs['user_idx'] = user_idx
		except Exception as e:
			import traceback
			print('[auth_user error]')
			traceback.print_exc()
				
		return f(*args, **kwargs)
	
	return decorated_function

def parse_token():
	secret = current_app.config.get('JWT_SECRET')
	alphabet = current_app.config.get('SQIDS_ALPHABET')
	if not secret or not alphabet: return None, None

	auth = request.headers.get('Authorization', '')
	if not auth.startswith('JWT '): return None, None

	payload = jwt.decode(auth[4:], secret, 'HS256', audience='feather')

	sqids = Sqids(min_length=7, alphabet=alphabet)
	user_idx = sqids.decode(payload['sub'])[0]
	print(user_idx, payload)
	return user_idx, payload

# 사용자 session token 발급 및 기록
def issue_token(idx: int) -> str:
	secret = current_app.config.get('JWT_SECRET')
	alphabet = current_app.config.get('SQIDS_ALPHABET')
	if not secret or not alphabet: return None
	
	sqids = Sqids(min_length=7, alphabet=alphabet)
	sub = sqids.encode([idx])

	now = int(datetime.datetime.now().timestamp())

	conn, cursor = gcc()

	device_idx = 0
	try:
		cursor.execute('SELECT `idx` FROM `feather_devices` WHERE `uuid` = %s;', (request.headers.get('X-Uuid'),))
		row = cursor.fetchone()
		device_idx = row['idx']
	except: pass

	remote_addr = request.headers.get('X-Forwarded-For', '') or request.remote_addr
	print(idx, now, device_idx, remote_addr)
	cursor.execute('INSERT INTO `feather_user_token` VALUES (NULL, %s, %s, %s, %s, 0);', (idx, now, device_idx, remote_addr,))
	conn.commit()
	
	payload = {'aud': 'feather', 'sub': sub, 'iat': now}
	return jwt.encode(payload, secret, 'HS256')


def get_user(idx: int, share=True):
	conn, cursor = gcc()
	cursor.execute('''SELECT
		U.`handle`, U.`name`, U.`email`, U.`image`,
		U.`agree_email`, U.`agree_push`, U.`agree_time`,
		UA.`about`, UA.`link_home`, UA.`link_instagram`, UA.`link_x`, UA.`link_tiktok`
	FROM `feather_users` U
	LEFT JOIN `feather_user_about` UA ON UA.`idx` = U.`idx`
	WHERE U.`is_deleted` = 0 AND U.`idx` = %s;''', (idx,))
	
	row = cursor.fetchone()

	if row is None: return None, None

	bool_columns(row, ('agree_email', 'agree_push'))
	group_column(row, 'agree')

	for key in ('about', 'link_home', 'link_instagram', 'link_x', 'link_tiktok'):
		if row[key] is None: row[key] = ''
	group_column(row, 'link')

	shares = []
	# TODO kyu share은 일부러 지금 코멘트아웃 해 둠.
	# if share:
	# 	cursor.execute('''SELECT
	# 		SR.`idx`, SR.`sid`, SR.`name`, SR.`icon`
	# 	FROM `share_users` SU
	# 	LEFT JOIN `share_root` SR ON SR.`idx` = SU.`share_idx`
	# 	WHERE SU.`user_idx` = %s AND SR.`is_deleted` = 0;''', (idx,))
	# 	shares = cursor.fetchall()
    
	return row, shares


def get_user_by_handle(handle: str):
	conn, cursor = gcc()
	cursor.execute('''SELECT
		U.`handle`, U.`name`, U.`email`, U.`image`,
		U.`agree_email`, U.`agree_push`, U.`agree_time`,
		UA.`about`, UA.`link_home`, UA.`link_instagram`, UA.`link_x`, UA.`link_tiktok`
	FROM `feather_users` U
	LEFT JOIN `feather_user_about` UA ON UA.`idx` = U.`idx`
	WHERE U.`is_deleted` = 0 AND U.`handle` = %s;''', (handle,))
	
	row = cursor.fetchone()

	if row is None:
		return None

	bool_columns(row, ('agree_email', 'agree_push'))
	group_column(row, 'agree')

	for key in ('about', 'link_home', 'link_instagram', 'link_x', 'link_tiktok'):
		if row[key] is None:
			row[key] = ''
	group_column(row, 'link')

	return row
    