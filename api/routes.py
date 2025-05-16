from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from .db import mysql

main_blueprint = Blueprint("main", __name__)

@main_blueprint.route('/health_check')
def health_check():
	return 'ok'

@main_blueprint.route('/robots.txt')
def robots_txt():
	return 'User-agent: *\nDisallow: /'
