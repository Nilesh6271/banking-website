"""
API-specific decorators that return JSON instead of redirecting
"""
from functools import wraps
from flask import jsonify, request
from flask_login import current_user

def api_login_required(f):
    """API version of login_required that returns JSON instead of redirecting"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required',
                'code': 'UNAUTHORIZED'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def api_role_required(role):
    """API version of role_required that returns JSON instead of redirecting"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({
                    'status': 'error',
                    'message': 'Authentication required',
                    'code': 'UNAUTHORIZED'
                }), 401
            
            if current_user.role != role:
                return jsonify({
                    'status': 'error',
                    'message': f'Access denied. Required role: {role}',
                    'code': 'FORBIDDEN'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def api_admin_required(f):
    """API version of admin_required that returns JSON instead of redirecting"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required',
                'code': 'UNAUTHORIZED'
            }), 401
        
        if current_user.role != 'admin':
            return jsonify({
                'status': 'error',
                'message': 'Admin access required',
                'code': 'FORBIDDEN'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function
