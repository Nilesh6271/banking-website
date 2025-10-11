# database/__init__.py
from flask_sqlalchemy import SQLAlchemy

# Initialize db object here (single source of truth)
db = SQLAlchemy()

# Import models AFTER db is defined to avoid circular imports
def init_db(app):
    """Initialize database with app context"""
    db.init_app(app)
    
    with app.app_context():
        # Import models here to register them with SQLAlchemy
        from .models import User, Token, ATMStatus, ChatbotFAQ, ChatLog, SystemLog
        
        # Create all tables
        db.create_all()
        
        print("Database initialized successfully")
        return db
