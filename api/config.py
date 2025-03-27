from dotenv import load_dotenv
import os

load_dotenv()
print("DB_PASSWORD:", os.getenv("DB_PASSWORD"))

class Config:
    MYSQL_DATABASE_HOST = os.getenv('DB_HOST')
    MYSQL_DATABASE_USER = os.getenv('DB_USER')
    MYSQL_DATABASE_PASSWORD = os.getenv('DB_PASSWORD')
    MYSQL_DATABASE_DB = os.getenv('DB_NAME')
    # SECRET_KEY = os.getenv('SECRET_KEY')  # Flask 세션용
