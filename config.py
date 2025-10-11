import os
from datetime import timedelta

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-super-secret-key-change-in-production'
    DEBUG = True
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), "bank_management.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Network settings
    HOST = '0.0.0.0'  # Listen on all network interfaces
    PORT = 5000
    
    # CORS settings
    CORS_ORIGINS = ['*']  # Allow all origins in local network
    
    # Token settings
    TOKEN_PREFIX = 'TKN'  # Format: TKN20251011001
    TOKEN_RESET_DAILY = True
    
    # SocketIO settings
    SOCKETIO_ASYNC_MODE = 'eventlet'
    SOCKETIO_CORS_ALLOWED_ORIGINS = '*'
    
    # Chatbot settings
    CHATBOT_EXCEL_PATH = 'data/BankBot_Data_Extended.xlsx'
    CHATBOT_CONFIDENCE_THRESHOLD = 0.65
    
    # Logging settings
    LOG_FILE = 'logs/app.log'
    LOG_LEVEL = 'INFO'
    
    # Pagination
    ITEMS_PER_PAGE = 20
