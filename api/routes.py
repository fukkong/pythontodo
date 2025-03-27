from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from .db import mysql

main_blueprint = Blueprint("main", __name__)

@main_blueprint.route('/', methods=["GET"])
def index():
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM todo;")
    rows = cursor.fetchall()
    result = []
    for row in rows:
        print (row)
        result.append({'id': row[0], 'title': row[1], 'completed': bool(row[2])})
    cursor.close()
    conn.close()
    return render_template('index.html', todos=result)

@main_blueprint.route('/api/todo', methods=["POST"])
def create_todo_list():
    data = request.form.get('task')  # form 방식일 땐 request.form 사용
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO todo (title) VALUES (%s)", (data))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/')

@main_blueprint.route('/api/todo/<int:todo_id>', methods=['PUT'])
def toggle_todo(todo_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE todo SET completed = NOT completed WHERE id = (%s)", (todo_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'status': 'ok'})

@main_blueprint.route('/api/todo/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todo WHERE id = (%s)", (todo_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'status': 'ok'})
