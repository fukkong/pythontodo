import flask
import os
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify

TODO_FILE = 'todos.json'

app = flask.Flask(__name__)

def load_todos():
    if not os.path.exists(TODO_FILE):
        with open(TODO_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
    with open(TODO_FILE, 'r', encoding='utf-8') as f:
        return json.load(f) 

def save_todos(todos):
    with open(TODO_FILE, 'w') as f:
        json.dump(todos, f, indent=4, ensure_ascii=False)


def get_next_id(todos):
    if not todos:
        return 1
    return max(todo["id"] for todo in todos) + 1

@app.route('/', methods=["GET"])
def index():
    todos = load_todos()
    return render_template('index.html', todos=todos)

@app.route('/api/todo', methods=["GET"])
def get_todo_list():
    # read
    return 'sth'

@app.route('/api/todo', methods=["POST"])
def create_todo_list():
    todos = load_todos()
    new_task = request.form.get('task', '').strip()
    print(new_task)
    if new_task:
        new_id = get_next_id(todos)
        todos.append({'id': new_id, 'task': new_task, 'done': False})
        save_todos(todos)
    return redirect(url_for('index'))

@app.route('/api/todo/<int:todo_id>', methods=['PUT'])
def toggle_todo(todo_id):
    todos = load_todos()
    for todo in todos:
        if todo['id'] == todo_id:
            todo['done'] = not todo['done']
            save_todos(todos)
            break
    return jsonify({'status': 'ok'})

@app.route('/api/todo/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    todos = load_todos()
    todos = [todo for todo in todos if todo['id'] != todo_id]
    print(todo_id)
    save_todos(todos)
    return jsonify({'status': 'ok'})

if __name__=='__main__':
    print(__name__,"서버 실행")
    app.run(port=5001, debug=True, threaded=True)
