import requests
import jwt
import base64
from cryptography.hazmat.primitives.asymmetric import rsa

class OAuthError(Exception): pass

def b64_to_int(b64):
	data = base64.urlsafe_b64decode(b64 + '==')
	return int.from_bytes(data, 'big')

# id_token 검증
JWK_CACHE = {}
def pub_key_for(header: dict, provider: str):
	cache_key = f"{provider}_{header['kid']}"
	
	if cache_key in JWK_CACHE:
		jwk = JWK_CACHE[cache_key]
		return rsa.RSAPublicNumbers(jwk['e'], jwk['n']).public_key()
	
	# https://ISS_HOST/.well-known/openid-configuration
	if provider == 'google':
		jwk_url = 'https://www.googleapis.com/oauth2/v3/certs'
	elif provider == 'apple':
		jwk_url = 'https://appleid.apple.com/auth/keys'
	else:
		raise OAuthError('Unexpected provider')
	
	pub_key = None
	j = requests.get(jwk_url).json()
	for jwk in j['keys']:
		if jwk['kid'] == header['kid']:
			# check algorithm
			if header['alg'] != jwk['alg']: continue # RS256
			
			e = b64_to_int(jwk['e'])
			n = b64_to_int(jwk['n'])
			
			JWK_CACHE[cache_key] = { 'e': e, 'n': n }
			pub_key = rsa.RSAPublicNumbers(e, n).public_key()
			break
	
	return pub_key


def verify_id_token(token: str, audience: str = None): # openid
	try:
		header = jwt.get_unverified_header(token)
		unverified = jwt.decode(token, options={'verify_signature': False})
	except:
		raise OAuthError('Invalid token')

	if unverified['iss'] in ('accounts.google.com', 'https://accounts.google.com'):
		provider = 'google'
	elif unverified['iss'] in ('https://appleid.apple.com'):
		provider = 'apple'
	else:
		raise OAuthError('Unknown issuer')
	
	pub_key = pub_key_for(header, provider)
	if pub_key is None:
		raise OAuthError('Failed to get jwk')
	
	try:
		# Google 기준 서명 키, Apple 기준 App/Service ID 에 따라 달라짐
		#aud = app.config(provider.upper() + '_OAUTH2_CLIENT_ID')
		aud = audience if audience is not None else unverified['aud']
		
		# header['alg']
		# , options={'verify_exp': False}
		decoded = jwt.decode(token, pub_key, algorithms=['RS256'], audience=aud)
		
		return provider, decoded
	
	except jwt.exceptions.ExpiredSignatureError as e:
		raise OAuthError('token expired')
	except Exception as e:
		# raise e
		raise OAuthError('Failed to decode id_token')
