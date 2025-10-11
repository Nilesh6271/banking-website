from flask import request
import re

def validate_required_fields(data, required_fields):
    """Validate that all required fields are present and not empty"""
    missing_fields = []
    
    for field in required_fields:
        if field not in data or not data[field] or str(data[field]).strip() == '':
            missing_fields.append(field)
    
    return missing_fields

def validate_user_data(data, is_update=False):
    """Validate user data for creation/update"""
    errors = []
    
    # Required fields for creation
    if not is_update:
        required_fields = ['username', 'password', 'role', 'full_name', 'email', 'phone']
        missing = validate_required_fields(data, required_fields)
        if missing:
            errors.append(f"Missing required fields: {', '.join(missing)}")
    
    # Validate username
    if 'username' in data:
        username = data['username'].strip()
        if len(username) < 3:
            errors.append("Username must be at least 3 characters long")
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors.append("Username can only contain letters, numbers, and underscores")
    
    # Validate password
    if 'password' in data:
        password = data['password']
        if len(password) < 6:
            errors.append("Password must be at least 6 characters long")
        if not re.search(r'[A-Za-z]', password):
            errors.append("Password must contain at least one letter")
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
    
    # Validate email
    if 'email' in data:
        email = data['email'].strip().lower()
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            errors.append("Invalid email format")
    
    # Validate phone
    if 'phone' in data:
        phone = data['phone'].strip()
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) not in [10, 11]:
            errors.append("Phone number must be 10 or 11 digits")
    
    # Validate role
    if 'role' in data:
        valid_roles = ['admin', 'staff', 'customer']
        if data['role'] not in valid_roles:
            errors.append(f"Role must be one of: {', '.join(valid_roles)}")
    
    # Validate account number for customers
    if 'role' in data and data['role'] == 'customer':
        if 'account_number' in data and data['account_number']:
            account_number = data['account_number'].strip()
            if len(account_number) < 8:
                errors.append("Account number must be at least 8 characters long")
    
    return errors

def validate_token_data(data):
    """Validate token generation data"""
    errors = []
    
    required_fields = ['service_type']
    missing = validate_required_fields(data, required_fields)
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    
    # Validate service type
    if 'service_type' in data:
        valid_types = ['cash_deposit', 'general_query', 'loan_application', 'meet_gm']
        if data['service_type'] not in valid_types:
            errors.append(f"Service type must be one of: {', '.join(valid_types)}")
    
    # Validate notes length
    if 'notes' in data and data['notes']:
        if len(data['notes']) > 500:
            errors.append("Notes must be less than 500 characters")
    
    return errors

def validate_atm_data(data):
    """Validate ATM status update data"""
    errors = []
    
    # Validate status
    if 'status' in data:
        valid_statuses = ['operational', 'out_of_service', 'low_cash', 'under_maintenance']
        if data['status'] not in valid_statuses:
            errors.append(f"Status must be one of: {', '.join(valid_statuses)}")
    
    # Validate queue length
    if 'queue_length' in data:
        try:
            queue_length = int(data['queue_length'])
            if queue_length < 0:
                errors.append("Queue length cannot be negative")
        except (ValueError, TypeError):
            errors.append("Queue length must be a valid number")
    
    # Validate notes length
    if 'notes' in data and data['notes']:
        if len(data['notes']) > 500:
            errors.append("Notes must be less than 500 characters")
    
    return errors

def validate_pagination_params(args):
    """Validate pagination parameters"""
    errors = []
    
    # Validate page
    if 'page' in args:
        try:
            page = int(args['page'])
            if page < 1:
                errors.append("Page must be greater than 0")
        except (ValueError, TypeError):
            errors.append("Page must be a valid number")
    
    # Validate limit
    if 'limit' in args:
        try:
            limit = int(args['limit'])
            if limit < 1 or limit > 100:
                errors.append("Limit must be between 1 and 100")
        except (ValueError, TypeError):
            errors.append("Limit must be a valid number")
    
    return errors

def sanitize_input(text):
    """Sanitize user input"""
    if not text:
        return text
    
    # Remove potentially dangerous characters
    text = str(text).strip()
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove script tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    return text
