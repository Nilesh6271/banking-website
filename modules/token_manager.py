from database import db
from database.models import Token, User
from flask_socketio import emit
from datetime import datetime, date
from utils.helpers import calculate_wait_time, generate_token_number
from config import Config

def generate_token(customer_id, service_type, notes=None):
    """
    Generate new token with automatic numbering
    
    Service types:
    - cash_deposit
    - general_query
    - loan_application
    - meet_gm
    """
    today = date.today()
    
    # Get last token of today
    last_token = Token.query.filter(
        db.func.date(Token.generated_at) == today
    ).order_by(Token.token_id.desc()).first()
    
    # Generate sequence number
    if last_token:
        last_number = int(last_token.token_number[-3:])
        sequence = last_number + 1
    else:
        sequence = 1
    
    # Format token number
    date_str = today.strftime('%Y%m%d')
    token_number = generate_token_number(Config.TOKEN_PREFIX, date_str, sequence)
    
    # Check priority
    customer = User.query.get(customer_id)
    priority = determine_priority(customer)
    
    # Create token
    token = Token(
        token_number=token_number,
        customer_id=customer_id,
        service_type=service_type,
        priority=priority,
        status='waiting',
        notes=notes
    )
    
    db.session.add(token)
    db.session.commit()
    
    # Calculate estimated wait time
    waiting_count = Token.query.filter_by(status='waiting').count()
    token.estimated_wait_time = calculate_wait_time(waiting_count)
    db.session.commit()
    
    return token

def determine_priority(customer):
    """Determine token priority based on customer attributes"""
    # This is a simple implementation - you can enhance based on your business rules
    if customer.role == 'admin':
        return 'vip'
    elif customer.account_number and 'VIP' in customer.account_number:
        return 'vip'
    else:
        return 'normal'

def get_waiting_tokens():
    """Get all waiting tokens ordered by priority and generation time"""
    return Token.query.filter_by(status='waiting').order_by(
        Token.priority.desc(),
        Token.generated_at.asc()
    ).all()

def get_token_by_id(token_id):
    """Get token by ID"""
    return Token.query.get(token_id)

def get_token_by_number(token_number):
    """Get token by token number"""
    return Token.query.filter_by(token_number=token_number).first()

def update_token_status(token_id, status, counter_number=None, notes=None, served_by=None):
    """Update token status"""
    token = get_token_by_id(token_id)
    if not token:
        return None
    
    old_status = token.status
    token.status = status
    
    if status == 'in_progress':
        token.called_at = datetime.utcnow()
        if counter_number:
            token.counter_number = counter_number
        if served_by:
            token.served_by = served_by
    elif status == 'completed':
        token.completed_at = datetime.utcnow()
        if served_by:
            token.served_by = served_by
    
    if notes:
        token.notes = notes
    
    db.session.commit()
    return token

def get_customer_tokens(customer_id, status=None, limit=50):
    """Get tokens for a specific customer"""
    query = Token.query.filter_by(customer_id=customer_id)
    
    if status:
        query = query.filter_by(status=status)
    
    return query.order_by(Token.generated_at.desc()).limit(limit).all()

def get_tokens_by_status(status, limit=100):
    """Get tokens by status"""
    return Token.query.filter_by(status=status).order_by(
        Token.generated_at.desc()
    ).limit(limit).all()

def get_tokens_by_date_range(start_date, end_date):
    """Get tokens within date range"""
    return Token.query.filter(
        Token.generated_at >= start_date,
        Token.generated_at <= end_date
    ).order_by(Token.generated_at.desc()).all()

def get_token_statistics():
    """Get token statistics"""
    total_tokens = Token.query.count()
    waiting_tokens = Token.query.filter_by(status='waiting').count()
    in_progress_tokens = Token.query.filter_by(status='in_progress').count()
    completed_tokens = Token.query.filter_by(status='completed').count()
    cancelled_tokens = Token.query.filter_by(status='cancelled').count()
    
    return {
        'total': total_tokens,
        'waiting': waiting_tokens,
        'in_progress': in_progress_tokens,
        'completed': completed_tokens,
        'cancelled': cancelled_tokens
    }

def get_service_type_breakdown():
    """Get breakdown of tokens by service type"""
    from sqlalchemy import func
    
    results = db.session.query(
        Token.service_type,
        func.count(Token.token_id).label('count')
    ).group_by(Token.service_type).all()
    
    return {result.service_type: result.count for result in results}

def cancel_token(token_id, customer_id):
    """Cancel a token (only if status is 'waiting')"""
    token = get_token_by_id(token_id)
    
    if not token:
        return {
            'status': 'error',
            'message': 'Token not found'
        }
    
    if token.customer_id != customer_id:
        return {
            'status': 'error',
            'message': 'Unauthorized to cancel this token'
        }
    
    if token.status != 'waiting':
        return {
            'status': 'error',
            'message': 'Only waiting tokens can be cancelled'
        }
    
    token.status = 'cancelled'
    db.session.commit()
    
    return {
        'status': 'success',
        'message': 'Token cancelled successfully'
    }

def get_next_token_to_call():
    """Get next token to call (highest priority, oldest first)"""
    return Token.query.filter_by(status='waiting').order_by(
        Token.priority.desc(),
        Token.generated_at.asc()
    ).first()

def call_next_token(counter_number, served_by):
    """Call the next token in queue"""
    token = get_next_token_to_call()
    
    if not token:
        return {
            'status': 'error',
            'message': 'No tokens in queue'
        }
    
    updated_token = update_token_status(
        token.token_id,
        'in_progress',
        counter_number=counter_number,
        served_by=served_by
    )
    
    return {
        'status': 'success',
        'message': f'Token {token.token_number} called to Counter {counter_number}',
        'token': updated_token.to_dict()
    }

def complete_token(token_id, served_by):
    """Complete a token"""
    token = get_token_by_id(token_id)
    
    if not token:
        return {
            'status': 'error',
            'message': 'Token not found'
        }
    
    if token.status != 'in_progress':
        return {
            'status': 'error',
            'message': 'Token is not in progress'
        }
    
    updated_token = update_token_status(
        token_id,
        'completed',
        served_by=served_by
    )
    
    return {
        'status': 'success',
        'message': 'Token completed successfully',
        'token': updated_token.to_dict()
    }
