from functools import wraps
from flask_login import current_user
from flask import jsonify, request
from database.models import SystemLog, db
from utils.helpers import get_client_ip
from datetime import datetime

def role_required(*roles):
    """Restrict access to specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            if current_user.role not in roles:
                return jsonify({'error': 'Access denied'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Require admin role"""
    return role_required('admin')(f)

def staff_required(f):
    """Require staff or admin role"""
    return role_required('staff', 'admin')(f)

def customer_required(f):
    """Require customer role"""
    return role_required('customer')(f)

def log_activity(action, details=None):
    """Decorator to log user activity"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            
            # Log the activity
            try:
                log_entry = SystemLog(
                    user_id=current_user.user_id if current_user.is_authenticated else None,
                    action=action,
                    details=details or f"Accessed {request.endpoint}",
                    ip_address=get_client_ip(),
                    timestamp=datetime.utcnow()
                )
                db.session.add(log_entry)
                db.session.commit()
            except Exception as e:
                # Don't fail the request if logging fails
                print(f"Failed to log activity: {str(e)}")
            
            return result
        return decorated_function
    return decorator

def validate_json_content_type(f):
    """Validate that request has JSON content type"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'PATCH']:
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
        return f(*args, **kwargs)
    return decorated_function

def handle_errors(f):
    """Handle common errors gracefully"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({'error': f'Invalid value: {str(e)}'}), 400
        except KeyError as e:
            return jsonify({'error': f'Missing required field: {str(e)}'}), 400
        except Exception as e:
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    return decorated_function

def rate_limit(max_requests=100, window_minutes=60):
    """Simple rate limiting decorator"""
    from collections import defaultdict
    import time
    
    # In-memory storage (use Redis in production)
    request_counts = defaultdict(list)
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = get_client_ip()
            current_time = time.time()
            window_seconds = window_minutes * 60
            
            # Clean old requests
            request_counts[client_ip] = [
                req_time for req_time in request_counts[client_ip]
                if current_time - req_time < window_seconds
            ]
            
            # Check rate limit
            if len(request_counts[client_ip]) >= max_requests:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': window_seconds
                }), 429
            
            # Record this request
            request_counts[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
