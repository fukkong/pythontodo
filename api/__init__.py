from flask import Flask
from .db import mysql
from .routes import main_blueprint

def create_app():
    app = Flask(__name__)
    
    app.config.from_object('api.config.Config')

    mysql.init_app(app)

    app.register_blueprint(main_blueprint)

    return app
