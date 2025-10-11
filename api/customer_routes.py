from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from modules.token_manager import generate_token, get_customer_tokens, cancel_token
from modules.atm_manager import get_all_atm_status
from modules.analytics import get_token_statistics
from utils.decorators import role_required, validate_json_content_type, handle_errors
from utils.validators import validate_token_data, validate_pagination_params
from utils.helpers import get_pagination_info
from database import db
from database.models import Token
from flask_socketio import emit

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/dashboard', methods=['GET'])
@login_required
@role_required('customer')
@handle_errors
def customer_dashboard():
    """Get customer dashboard data"""
    # Get customer profile
    profile = current_user.to_dict()
    
    # Get active tokens
    active_tokens = get_customer_tokens(current_user.user_id, status='waiting')
    active_tokens.extend(get_customer_tokens(current_user.user_id, status='in_progress'))
    
    # Get recent tokens
    recent_tokens = get_customer_tokens(current_user.user_id, limit=10)
    
    # Get ATM status
    atm_status = get_all_atm_status()
    
    # Get token statistics
    token_stats = get_token_statistics()
    
    return jsonify({
        'status': 'success',
        'profile': profile,
        'active_tokens': [token.to_dict() for token in active_tokens],
        'recent_tokens': [token.to_dict() for token in recent_tokens],
        'atm_status': [atm.to_dict() for atm in atm_status],
        'statistics': token_stats
    })

@customer_bp.route('/token/generate', methods=['POST'])
@login_required
@role_required('customer')
@validate_json_content_type
@handle_errors
def generate_customer_token():
    """Generate new token for customer"""
    data = request.get_json()
    
    # Validate token data
    errors = validate_token_data(data)
    if errors:
        return jsonify({
            'status': 'error',
            'message': 'Validation errors',
            'errors': errors
        }), 400
    
    service_type = data['service_type']
    notes = data.get('notes', '')
    
    # Generate token
    token = generate_token(current_user.user_id, service_type, notes)
    
    # Emit WebSocket event
    emit('token_generated', {
        'token': token.to_dict()
    }, room='staff')
    
    emit('token_generated', {
        'token': token.to_dict()
    }, room='admin')
    
    return jsonify({
        'status': 'success',
        'message': f'Token {token.token_number} generated successfully',
        'token': token.to_dict()
    })

@customer_bp.route('/token/history', methods=['GET'])
@login_required
@role_required('customer')
@handle_errors
def get_token_history():
    """Get customer token history"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    status = request.args.get('status')
    
    # Validate pagination
    errors = validate_pagination_params(request.args)
    if errors:
        return jsonify({
            'status': 'error',
            'message': 'Invalid pagination parameters',
            'errors': errors
        }), 400
    
    # Get tokens
    query = Token.query.filter_by(customer_id=current_user.user_id)
    
    if status:
        query = query.filter_by(status=status)
    
    tokens = query.order_by(Token.generated_at.desc()).paginate(
        page=page, per_page=limit, error_out=False
    )
    
    return jsonify({
        'status': 'success',
        'tokens': [token.to_dict() for token in tokens.items],
        'pagination': get_pagination_info(page, limit, tokens.total)
    })

@customer_bp.route('/token/<int:token_id>', methods=['GET'])
@login_required
@role_required('customer')
@handle_errors
def get_token_details(token_id):
    """Get specific token details"""
    token = Token.query.filter_by(
        token_id=token_id,
        customer_id=current_user.user_id
    ).first()
    
    if not token:
        return jsonify({
            'status': 'error',
            'message': 'Token not found'
        }), 404
    
    return jsonify({
        'status': 'success',
        'token': token.to_dict()
    })

@customer_bp.route('/token/<int:token_id>', methods=['DELETE'])
@login_required
@role_required('customer')
@handle_errors
def cancel_customer_token(token_id):
    """Cancel customer token"""
    result = cancel_token(token_id, current_user.user_id)
    
    if result['status'] == 'error':
        return jsonify(result), 400
    
    # Emit WebSocket event
    emit('token_updated', {
        'token': {'token_id': token_id, 'status': 'cancelled'}
    }, room='staff')
    
    emit('token_updated', {
        'token': {'token_id': token_id, 'status': 'cancelled'}
    }, room='admin')
    
    return jsonify(result)

@customer_bp.route('/atm-status', methods=['GET'])
@login_required
@role_required('customer')
@handle_errors
def get_atm_status():
    """Get ATM status for customers"""
    atm_status = get_all_atm_status()
    
    return jsonify({
        'status': 'success',
        'atms': [atm.to_dict() for atm in atm_status]
    })

@customer_bp.route('/profile', methods=['GET'])
@login_required
@role_required('customer')
@handle_errors
def get_customer_profile():
    """Get customer profile"""
    return jsonify({
        'status': 'success',
        'profile': current_user.to_dict()
    })

@customer_bp.route('/profile', methods=['PUT'])
@login_required
@role_required('customer')
@validate_json_content_type
@handle_errors
def update_customer_profile():
    """Update customer profile"""
    data = request.get_json()
    
    # Update allowed fields
    if 'phone' in data:
        current_user.phone = data['phone']
    
    if 'email' in data:
        current_user.email = data['email']
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Profile updated successfully',
        'profile': current_user.to_dict()
    })

@customer_bp.route('/notifications', methods=['GET'])
@login_required
@role_required('customer')
@handle_errors
def get_customer_notifications():
    """Get customer notifications"""
    # Get recent tokens that were called
    called_tokens = Token.query.filter_by(
        customer_id=current_user.user_id,
        status='in_progress'
    ).order_by(Token.called_at.desc()).limit(10).all()
    
    notifications = []
    for token in called_tokens:
        notifications.append({
            'type': 'token_called',
            'title': 'Your Token Called',
            'message': f'Token {token.token_number} has been called to Counter {token.counter_number}',
            'timestamp': token.called_at.isoformat() if token.called_at else None,
            'token_id': token.token_id
        })
    
    return jsonify({
        'status': 'success',
        'notifications': notifications
    })
