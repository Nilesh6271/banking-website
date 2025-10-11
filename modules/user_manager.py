from database import db
from database.models import User, SystemLog
from flask_login import current_user
from utils.helpers import get_client_ip
from datetime import datetime
from sqlalchemy import or_
import bcrypt

def get_all_users(role=None, status=None, page=1, per_page=20):
    """Get all users with optional filtering"""
    query = User.query
    
    if role:
        query = query.filter_by(role=role)
    
    if status:
        query = query.filter_by(status=status)
    
    return query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

def get_user_by_id(user_id):
    """Get user by ID"""
    return User.query.get(user_id)

def get_user_by_username(username):
    """Get user by username"""
    return User.query.filter_by(username=username).first()

def get_user_by_email(email):
    """Get user by email"""
    return User.query.filter_by(email=email).first()

def search_users(search_term, role=None):
    """Search users by name, username, or email"""
    query = User.query.filter(
        or_(
            User.full_name.ilike(f'%{search_term}%'),
            User.username.ilike(f'%{search_term}%'),
            User.email.ilike(f'%{search_term}%')
        )
    )
    
    if role:
        query = query.filter_by(role=role)
    
    return query.order_by(User.full_name).all()

def create_user(user_data, created_by=None):
    """Create new user"""
    # Check if username already exists
    if get_user_by_username(user_data['username']):
        return {
            'status': 'error',
            'message': 'Username already exists'
        }
    
    # Check if email already exists
    if get_user_by_email(user_data['email']):
        return {
            'status': 'error',
            'message': 'Email already exists'
        }
    
    # Hash password
    password_hash = bcrypt.hashpw(
        user_data['password'].encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    # Create user
    user = User(
        username=user_data['username'],
        password_hash=password_hash,
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
        ip_address='127.0.0.1',  # Default IP for system operations
        timestamp=datetime.utcnow()
    )
    db.session.add(log_entry)
    db.session.commit()
    
    return {
        'status': 'success',
        'message': 'User created successfully',
        'user': user.to_dict()
    }

def update_user(user_id, update_data, updated_by=None):
    """Update user information"""
    user = get_user_by_id(user_id)
    
    if not user:
        return {
            'status': 'error',
            'message': 'User not found'
        }
    
    # Update allowed fields
    if 'full_name' in update_data:
        user.full_name = update_data['full_name']
    
    if 'email' in update_data:
        # Check if email is already taken by another user
        existing_user = get_user_by_email(update_data['email'])
        if existing_user and existing_user.user_id != user_id:
            return {
                'status': 'error',
                'message': 'Email already exists'
            }
        user.email = update_data['email']
    
    if 'phone' in update_data:
        user.phone = update_data['phone']
    
    if 'account_number' in update_data:
        user.account_number = update_data['account_number']
    
    if 'status' in update_data:
        user.status = update_data['status']
    
    db.session.commit()
    
    # Log user update
    log_entry = SystemLog(
        user_id=updated_by.user_id if updated_by else None,
        action='user_updated',
        details=f'Updated user {user.username}',
        ip_address=get_client_ip(),
        timestamp=datetime.utcnow()
    )
    db.session.add(log_entry)
    db.session.commit()
    
    return {
        'status': 'success',
        'message': 'User updated successfully',
        'user': user.to_dict()
    }

def delete_user(user_id, deleted_by=None):
    """Soft delete user (set status to inactive)"""
    user = get_user_by_id(user_id)
    
    if not user:
        return {
            'status': 'error',
            'message': 'User not found'
        }
    
    # Don't allow deleting admin users
    if user.role == 'admin':
        return {
            'status': 'error',
            'message': 'Cannot delete admin users'
        }
    
    user.status = 'inactive'
    db.session.commit()
    
    # Log user deletion
    log_entry = SystemLog(
        user_id=deleted_by.user_id if deleted_by else None,
        action='user_deleted',
        details=f'Deleted user {user.username}',
        ip_address=get_client_ip(),
        timestamp=datetime.utcnow()
    )
    db.session.add(log_entry)
    db.session.commit()
    
    return {
        'status': 'success',
        'message': 'User deleted successfully'
    }

def reset_user_password(user_id, new_password, reset_by=None):
    """Reset user password"""
    user = get_user_by_id(user_id)
    
    if not user:
        return {
            'status': 'error',
            'message': 'User not found'
        }
    
    # Hash new password
    password_hash = bcrypt.hashpw(
        new_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    user.password_hash = password_hash
    db.session.commit()
    
    # Log password reset
    log_entry = SystemLog(
        user_id=reset_by.user_id if reset_by else None,
        action='password_reset',
        details=f'Reset password for user {user.username}',
        ip_address=get_client_ip(),
        timestamp=datetime.utcnow()
    )
    db.session.add(log_entry)
    db.session.commit()
    
    return {
        'status': 'success',
        'message': 'Password reset successfully'
    }

def get_user_statistics():
    """Get user statistics"""
    total_users = User.query.count()
    admin_users = User.query.filter_by(role='admin').count()
    staff_users = User.query.filter_by(role='staff').count()
    customer_users = User.query.filter_by(role='customer').count()
    active_users = User.query.filter_by(status='active').count()
    inactive_users = User.query.filter_by(status='inactive').count()
    
    return {
        'total': total_users,
        'admin': admin_users,
        'staff': staff_users,
        'customer': customer_users,
        'active': active_users,
        'inactive': inactive_users
    }

def get_recent_users(limit=10):
    """Get recently created users"""
    return User.query.order_by(User.created_at.desc()).limit(limit).all()

def get_user_activity(user_id, days=30):
    """Get user activity logs"""
    from datetime import timedelta
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    return SystemLog.query.filter(
        SystemLog.user_id == user_id,
        SystemLog.timestamp >= start_date
    ).order_by(SystemLog.timestamp.desc()).all()

def create_default_admin():
    """Create default admin user if not exists"""
    admin = get_user_by_username('admin')
    if not admin:
        password_hash = bcrypt.hashpw(
            'admin123'.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        admin = User(
            username='admin',
            password_hash=password_hash,
            role='admin',
            full_name='System Administrator',
            email='admin@apexbank.com',
            phone='1800-123-4567',
            status='active'
        )
        
        db.session.add(admin)
        db.session.commit()
        
        return True
    
    return False

def create_test_users():
    """Create test users for development"""
    test_users = [
        {
            'username': 'staff1',
            'password': 'staff123',
            'role': 'staff',
            'full_name': 'Rajesh Kumar',
            'email': 'rajesh@apexbank.com',
            'phone': '9876543210'
        },
        {
            'username': 'staff2',
            'password': 'staff123',
            'role': 'staff',
            'full_name': 'Priya Sharma',
            'email': 'priya@apexbank.com',
            'phone': '9876543211'
        },
        {
            'username': 'customer1',
            'password': 'cust123',
            'role': 'customer',
            'full_name': 'Amit Patel',
            'email': 'amit@email.com',
            'phone': '9876543220',
            'account_number': 'ACC123456789'
        },
        {
            'username': 'customer2',
            'password': 'cust123',
            'role': 'customer',
            'full_name': 'Sneha Reddy',
            'email': 'sneha@email.com',
            'phone': '9876543221',
            'account_number': 'ACC123456790'
        }
    ]
    
    created_count = 0
    for user_data in test_users:
        existing = get_user_by_username(user_data['username'])
        if not existing:
            result = create_user(user_data)
            if result['status'] == 'success':
                created_count += 1
    
    return created_count
