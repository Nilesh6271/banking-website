from datetime import datetime, timedelta
from flask import request
import json

def get_client_ip():
    """Get client IP address"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    return request.environ.get('REMOTE_ADDR')

def format_datetime(dt):
    """Format datetime for JSON serialization"""
    if dt is None:
        return None
    return dt.isoformat()

def calculate_wait_time(waiting_count, avg_service_time=5):
    """Calculate estimated wait time in minutes"""
    return waiting_count * avg_service_time

def generate_token_number(prefix, date_str, sequence):
    """Generate token number in format: PREFIX + DATE + SEQUENCE"""
    return f"{prefix}{date_str}{sequence:03d}"

def get_date_range(days=30):
    """Get date range for analytics"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date

def safe_json_loads(json_str, default=None):
    """Safely load JSON string"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def format_phone_number(phone):
    """Format phone number"""
    if not phone:
        return phone
    
    # Remove all non-digit characters
    digits = ''.join(filter(str.isdigit, phone))
    
    # Format based on length
    if len(digits) == 10:
        return f"{digits[:5]} {digits[5:]}"
    elif len(digits) == 11 and digits[0] == '0':
        return f"{digits[1:6]} {digits[6:]}"
    else:
        return phone

def validate_email(email):
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Basic phone validation"""
    import re
    # Remove all non-digit characters
    digits = ''.join(filter(str.isdigit, phone))
    # Check if it's 10 or 11 digits
    return len(digits) in [10, 11]

def get_pagination_info(page, per_page, total):
    """Get pagination information"""
    total_pages = (total + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    return {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_num': page - 1 if has_prev else None,
        'next_num': page + 1 if has_next else None
    }
