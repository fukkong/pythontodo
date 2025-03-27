from flask import Flask, request, jsonify, render_template, redirect, url_for
from flaskext.mysql import MySQL
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['MYSQL_DATABASE_HOST'] = os.getenv('DB_HOST')
app.config['MYSQL_DATABASE_USER'] = os.getenv('DB_USER')
app.config['MYSQL_DATABASE_PASSWORD'] = os.getenv('DB_PASSWORD')
app.config['MYSQL_DATABASE_DB'] = os.getenv('DB_NAME')

mysql = MySQL()
mysql.init_app(app)

@app.route('/', methods=["GET"])
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
    print('result is', result)
    # todos = jsonify(result)
    # print('what the fuck',todos)
    return render_template('index.html', todos=result)

@app.route('/api/todo', methods=["POST"])
def create_todo_list():
    data = request.form.get('task')  # form 방식일 땐 request.form 사용
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO todo (title) VALUES (%s)", (data))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/api/todo/<int:todo_id>', methods=['PUT'])
def toggle_todo(todo_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE todo SET completed = NOT completed WHERE id = (%s)", (todo_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/todo/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROMtodo WHERE id = (%s)", (todo_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'status': 'ok'})

if __name__=='__main__':
    print(__name__,"서버 실행")
    app.run(port=5001, debug=True, threaded=True)
