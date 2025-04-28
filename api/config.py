from dotenv import load_dotenv
import os

load_dotenv()
print("DB_PASSWORD:", os.getenv("DB_PASSWORD"))

class Config:
    # DB
    MYSQL_DATABASE_HOST = os.getenv('DB_HOST')
    MYSQL_DATABASE_USER = os.getenv('DB_USER')
    MYSQL_DATABASE_PASSWORD = os.getenv('DB_PASSWORD')
    MYSQL_DATABASE_DB = os.getenv('DB_NAME')

    # s3
    AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION')
    BUCKET_NAM= os.getenv('BUCKET_NAME')

    # sign-in / login
    GOOGLE_OAUTH2_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_OAUTH2_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    JWT_SECRET = os.getenv('JWT_SECRET')
    SQIDS_ALPHABET = os.getenv('SQIDS_ALPHABET')

    # SECRET_KEY = os.getenv('SECRET_KEY')  # Flask 세션용

