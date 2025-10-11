from flask_login import login_user, logout_user, current_user
from flask import session, request
from database import db
from database.models import User, SystemLog
from utils.helpers import get_client_ip
from datetime import datetime
import bcrypt

def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def authenticate_user(username, password):
    """Authenticate user with username and password"""
    user = User.query.filter_by(username=username).first()
    
    if user and verify_password(password, user.password_hash):
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Log login activity
        log_entry = SystemLog(
            user_id=user.user_id,
            action='login',
            details=f'User {username} logged in',
            ip_address=get_client_ip(),
            timestamp=datetime.utcnow()
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return user
    
    return None

def login_user_session(user, remember=False):
    """Login user and create session"""
    login_user(user, remember=remember)
    session.permanent = True
    
    return {
        'status': 'success',
        'message': 'Login successful',
        'user': user.to_dict()
    }

def logout_user_session():
    """Logout user and destroy session"""
    if current_user.is_authenticated:
        # Log logout activity
        log_entry = SystemLog(
            user_id=current_user.user_id,
            action='logout',
            details=f'User {current_user.username} logged out',
            ip_address=get_client_ip(),
            timestamp=datetime.utcnow()
        )
        db.session.add(log_entry)
        db.session.commit()
    
    logout_user()
    session.clear()
    
    return {
        'status': 'success',
        'message': 'Logout successful'
    }

def change_password(user, old_password, new_password):
    """Change user password"""
    # Verify old password
    if not verify_password(old_password, user.password_hash):
        return {
            'status': 'error',
            'message': 'Current password is incorrect'
        }
    
    # Validate new password
    if len(new_password) < 6:
        return {
            'status': 'error',
            'message': 'New password must be at least 6 characters long'
        }
    
    # Update password
    user.password_hash = hash_password(new_password)
    db.session.commit()
    
    # Log password change
    log_entry = SystemLog(
        user_id=user.user_id,
        action='password_changed',
        details='User changed password',
        ip_address=get_client_ip(),
        timestamp=datetime.utcnow()
    )
    db.session.add(log_entry)
    db.session.commit()
    
    return {
        'status': 'success',
        'message': 'Password changed successfully'
    }

def get_user_session():
    """Get current user session info"""
    if current_user.is_authenticated:
        return {
            'authenticated': True,
            'user': current_user.to_dict()
        }
    else:
        return {
            'authenticated': False,
            'user': None
        }

def check_user_permissions(user, required_role):
    """Check if user has required role"""
    if not user:
        return False
    
    # Admin has all permissions
    if user.role == 'admin':
        return True
    
    # Check specific role
    return user.role == required_role

def get_user_by_id(user_id):
    """Get user by ID"""
    return User.query.get(user_id)

def get_user_by_username(username):
    """Get user by username"""
    return User.query.filter_by(username=username).first()

def create_user(user_data, created_by=None):
    """Create new user"""
    # Check if username already exists
    if User.query.filter_by(username=user_data['username']).first():
        return {
            'status': 'error',
            'message': 'Username already exists'
        }
    
    # Check if email already exists
    if User.query.filter_by(email=user_data['email']).first():
        return {
            'status': 'error',
            'message': 'Email already exists'
        }
    
    # Create user
    user = User(
        username=user_data['username'],
        password_hash=hash_password(user_data['password']),
        role=user_data['role'],
        full_name=user_data['full_name'],
        email=user_data['email'],
        phone=user_data['phone'],
        account_number=user_data.get('account_number'),
        created_by=created_by.user_id if created_by else None
    )
    
    db.session.add(user)
    db.session.commit()
    
    # Log user creation
    log_entry = SystemLog(
        user_id=created_by.user_id if created_by else None,
        action='user_created',
        details=f'Created user {user_data["username"]} with role {user_data["role"]}',
        ip_address=get_client_ip(),
        timestamp=datetime.utcnow()
    )
    db.session.add(log_entry)
    db.session.commit()
    
    return {
        'status': 'success',
        'message': 'User created successfully',
        'user': user.to_dict()
    }
