from flask import Blueprint
app = Blueprint('pro', __name__)

from . import oauth
from . import user
from . import gallery

@app.route('/health_check')
def health_check():
	return 'ok'

@app.route('/robots.txt')
def robots_txt():
	return 'User-agent: *\nDisallow: /'
