import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///chat.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    NICKNAME_URL = 'https://www.qmsjmfb.com/erciyuan.php'
    NICKNAME_TIMEOUT = 5
    MESSAGES_PER_PAGE = 50
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
