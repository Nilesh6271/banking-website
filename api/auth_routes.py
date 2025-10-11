from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from database import db
from database.models import User, SystemLog
from modules.auth import authenticate_user, login_user_session, logout_user_session, change_password, get_user_session
from utils.decorators import validate_json_content_type, handle_errors
from utils.validators import validate_required_fields
import bcrypt
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
@validate_json_content_type
@handle_errors
def login():
    """User login endpoint"""
    data = request.get_json()
    
    # Validate required fields
    missing_fields = validate_required_fields(data, ['username', 'password'])
    if missing_fields:
        return jsonify({
            'status': 'error',
            'message': f'Missing required fields: {", ".join(missing_fields)}'
        }), 400
    
    username = data['username'].strip()
    password = data['password']
    remember = data.get('remember', False)
    
    # Authenticate user
    user = authenticate_user(username, password)
    
    if user:
        if user.status != 'active':
            return jsonify({
                'status': 'error',
                'message': 'Account is inactive. Please contact administrator.'
            }), 403
        
        # Login user
        result = login_user_session(user, remember)
        return jsonify(result)
    else:
        return jsonify({
            'status': 'error',
            'message': 'Invalid username or password'
        }), 401

@auth_bp.route('/logout', methods=['POST'])
@login_required
@handle_errors
def logout():
    """User logout endpoint"""
    result = logout_user_session()
    return jsonify(result)

@auth_bp.route('/session', methods=['GET'])
@handle_errors
def session():
    """Check user session"""
    result = get_user_session()
    return jsonify(result)

@auth_bp.route('/change-password', methods=['POST'])
@login_required
@validate_json_content_type
@handle_errors
def change_user_password():
    """Change user password"""
    data = request.get_json()
    
    # Validate required fields
    missing_fields = validate_required_fields(data, ['old_password', 'new_password'])
    if missing_fields:
        return jsonify({
            'status': 'error',
            'message': f'Missing required fields: {", ".join(missing_fields)}'
        }), 400
    
    old_password = data['old_password']
    new_password = data['new_password']
    
    # Change password
    result = change_password(current_user, old_password, new_password)
    
    if result['status'] == 'error':
        return jsonify(result), 400
    
    return jsonify(result)

@auth_bp.route('/profile', methods=['GET'])
@login_required
@handle_errors
def get_profile():
    """Get user profile"""
    return jsonify({
        'status': 'success',
        'user': current_user.to_dict()
    })

@auth_bp.route('/profile', methods=['PUT'])
@login_required
@validate_json_content_type
@handle_errors
def update_profile():
    """Update user profile"""
    data = request.get_json()
    
    # Update allowed fields
    if 'phone' in data:
        current_user.phone = data['phone']
    
    if 'email' in data:
        current_user.email = data['email']
    
    from database import db
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Profile updated successfully',
        'user': current_user.to_dict()
    })
