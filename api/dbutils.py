from flask import current_app

from . import mysql

def gcc():
	conn = mysql.get_db()
	cursor = conn.cursor()

	return conn, cursor


def group_column(row: dict, prefix: str):
	grp = {}
	
	prefix_ = prefix + '_'
	offset = len(prefix_)
	for key, val in row.items():
		if not key.startswith(prefix_): continue
		grp[key[offset:]] = val
	
	if len(grp) > 0:
		row[prefix] = grp
	
	for key in grp.keys():
		del row[prefix_ + key]


def bool_columns(row: dict, columns):
	for col in columns:
		if col in row:
			row[col] = bool(row[col])
