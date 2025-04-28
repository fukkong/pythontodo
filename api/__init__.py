from flask import Flask
from .db import mysql
from .routes import main_blueprint
from flask_cors import CORS
from . import pro



def create_app():
    app = Flask(__name__)
    CORS(app,origins=["https://mark.local.softsket.ch", "http://localhost:8000","http://localhost:5173"], supports_credentials=True)

    app.config.from_object('api.config.Config')
    
    mysql.init_app(app)

    app.register_blueprint(main_blueprint)
    app.register_blueprint(pro.app, url_prefix='/api/v1')

    return app
