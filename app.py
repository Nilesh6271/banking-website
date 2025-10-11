from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_cors import CORS
from config import Config
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from functools import wraps

# Import db from database package (not from models)
from database import db, init_db
from database.models import User

# Initialize extensions
login_manager = LoginManager()
socketio = SocketIO()
cors = CORS()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize database
    init_db(app)
    
    # Initialize other extensions
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    
    socketio.init_app(
        app, 
        cors_allowed_origins=app.config['SOCKETIO_CORS_ALLOWED_ORIGINS'],
        async_mode=app.config['SOCKETIO_ASYNC_MODE']
    )
    
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
    
    # Setup logging
    setup_logging(app)
    
    # Create default data
    with app.app_context():
        create_default_admin()
        initialize_atm_status()
        import_chatbot_data()
        create_test_users()
    
    # Register blueprints
    from api.auth_routes import auth_bp
    from api.customer_routes import customer_bp
    from api.staff_routes import staff_bp
    from api.admin_routes import admin_bp
    from api.chatbot_routes import chatbot_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(customer_bp, url_prefix='/api/customer')
    app.register_blueprint(staff_bp, url_prefix='/api/staff')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(chatbot_bp, url_prefix='/api/chatbot')
    
    # Register websocket events
    from websocket.events import register_socketio_events
    register_socketio_events(socketio)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register page routes
    register_page_routes(app)
    
    # Initialize chatbot
    with app.app_context():
        try:
            from modules.chatbot_integration import initialize_chatbot
            initialize_chatbot(app.config['CHATBOT_EXCEL_PATH'])
        except Exception as e:
            app.logger.warning(f"Chatbot initialization failed: {str(e)}")
    
    app.logger.info('Bank Management Server started successfully')
    
    return app

def setup_logging(app):
    """Configure application logging"""
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    app.logger.addHandler(file_handler)
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))

def create_default_admin():
    """Create default admin user if not exists"""
    import bcrypt
    
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        admin = User(
            username='admin',
            password_hash=password_hash.decode('utf-8'),
            role='admin',
            full_name='System Administrator',
            email='admin@apexbank.com',
            phone='1800-123-4567',
            status='active'
        )
        db.session.add(admin)
        db.session.commit()
        print("Default admin created - Username: admin, Password: admin123")

def initialize_atm_status():
    """Initialize ATM status data"""
    from database.models import ATMStatus
    
    if ATMStatus.query.count() == 0:
        atms = [
            ATMStatus(atm_name='ATM-01', location='Main Branch Lobby', status='operational'),
            ATMStatus(atm_name='ATM-02', location='Branch Exterior', status='operational'),
            ATMStatus(atm_name='ATM-03', location='Shopping Mall Branch', status='operational'),
        ]
        db.session.add_all(atms)
        db.session.commit()
        print("ATM status initialized")

def import_chatbot_data():
    """Import chatbot data from Excel into database"""
    from database.models import ChatbotFAQ
    import pandas as pd
    import json
    
    if ChatbotFAQ.query.count() == 0:
        excel_path = Config.CHATBOT_EXCEL_PATH
        if os.path.exists(excel_path):
            sheets = ['Definitions', 'DepositRates', 'LoanRates', 'BankInfo', 'Forms']
            for sheet in sheets:
                try:
                    df = pd.read_excel(excel_path, sheet_name=sheet)
                    for _, row in df.iterrows():
                        if not row.isnull().all():  # Skip empty rows
                            faq = ChatbotFAQ(
                                sheet_name=sheet,
                                category=sheet,
                                data_json=json.dumps(row.to_dict(), default=str)
                            )
                            db.session.add(faq)
                    db.session.commit()
                except Exception as e:
                    print(f"Error importing {sheet}: {str(e)}")
            print("Chatbot data imported")
        else:
            print(f"Excel file not found: {excel_path}")

def create_test_users():
    """Create test users for development"""
    from modules.user_manager import create_test_users
    created_count = create_test_users()
    if created_count > 0:
        print(f"✓ Created {created_count} test users")

def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return {'error': 'Resource not found'}, 404
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return {'error': 'Internal server error'}, 500
        return render_template('500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        if request.path.startswith('/api/'):
            return {'error': 'Access forbidden'}, 403
        return render_template('403.html'), 403

def register_page_routes(app):
    """Register page routes"""
    from flask_login import login_required, current_user
    from functools import wraps
    
    def role_required_page(role):
        """Decorator for role-based page access"""
        def decorator(f):
            @wraps(f)
            @login_required
            def decorated_function(*args, **kwargs):
                if current_user.role != role:
                    return redirect(url_for('login'))
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    @app.route('/')
    def home():
        return render_template('index.html')
    
    @app.route('/login')
    def login():
        return render_template('login.html')
    
    @app.route('/chatbot')
    def chatbot_page():
        return render_template('chatbot.html')
    
    @app.route('/services')
    def services():
        return render_template('services.html')
    
    @app.route('/rates')
    def rates():
        return render_template('rates.html')
    
    @app.route('/forms')
    def forms():
        return render_template('forms.html')
    
    @app.route('/contact')
    def contact():
        return render_template('contact.html')
    
    @app.route('/customer/dashboard')
    @role_required_page('customer')
    def customer_dashboard():
        return render_template('customer_dashboard.html')
    
    @app.route('/staff/dashboard')
    @role_required_page('staff')
    def staff_dashboard():
        return render_template('staff_dashboard.html')
    
    @app.route('/admin/dashboard')
    @role_required_page('admin')
    def admin_dashboard():
        return render_template('admin_dashboard.html')

@login_manager.user_loader
def load_user(user_id):
    from database.models import User
    return User.query.get(int(user_id))

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, 
                host=app.config['HOST'], 
                port=app.config['PORT'],
                debug=app.config['DEBUG'],
                allow_unsafe_werkzeug=True)  # For development only