from flask import Blueprint, request, jsonify
from flask_login import current_user
from modules.token_manager import (
    get_waiting_tokens, get_tokens_by_status, update_token_status,
    call_next_token, complete_token, get_token_by_id
)
from modules.atm_manager import (
    get_all_atm_status, update_atm_status, get_atm_by_id
)
from modules.analytics import get_staff_performance, get_token_statistics
from utils.decorators import validate_json_content_type, handle_errors
from utils.api_decorators import api_login_required, api_role_required
from utils.validators import validate_atm_data, validate_pagination_params
from utils.helpers import get_pagination_info
from database import db
from database.models import Token
from flask_socketio import emit
from datetime import datetime, timedelta
from sqlalchemy import func, and_

staff_bp = Blueprint('staff', __name__)

@staff_bp.route('/dashboard', methods=['GET'])
@api_login_required
@api_role_required('staff')
@handle_errors
def staff_dashboard():
    """Get staff dashboard data with comprehensive statistics"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    # Get today's tokens
    today_tokens = Token.query.filter(
        and_(
            Token.generated_at >= today,
            Token.generated_at < tomorrow
        )
    )
    
    # Count by status
    waiting_count = today_tokens.filter(Token.status == 'waiting').count()
    in_progress_count = today_tokens.filter(Token.status == 'in_progress').count()
    completed_count = today_tokens.filter(Token.status == 'completed').count()
    
    # Calculate average service time
    completed_tokens = today_tokens.filter(
        and_(
            Token.status == 'completed',
            Token.called_at.isnot(None),
            Token.completed_at.isnot(None)
        )
    ).all()
    
    if completed_tokens:
        total_time = sum([
            (token.completed_at - token.called_at).total_seconds() / 60
            for token in completed_tokens
        ])
        avg_service_time = round(total_time / len(completed_tokens))
    else:
        avg_service_time = 0
    
    # Get token queue (waiting and in_progress)
    token_queue = Token.query.filter(
        and_(
            Token.status.in_(['waiting', 'in_progress']),
            Token.generated_at >= today
        )
    ).order_by(Token.generated_at).all()
    
    # Get ATM status
    atm_status = get_all_atm_status()
    
    return jsonify({
        'status': 'success',
        'waiting': waiting_count,
        'in_progress': in_progress_count,
        'completed_today': completed_count,
        'avg_service_time': avg_service_time,
        'token_queue': [token.to_dict() for token in token_queue],
        'atm_status': [atm.to_dict() for atm in atm_status]
    })

@staff_bp.route('/tokens', methods=['GET'])
@api_login_required
@api_role_required('staff')
@handle_errors
def get_staff_tokens():
    """Get tokens for staff management"""
    # Get query parameters
    status = request.args.get('status')
    date = request.args.get('date')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    # Validate pagination
    errors = validate_pagination_params(request.args)
    if errors:
        return jsonify({
            'status': 'error',
            'message': 'Invalid pagination parameters',
            'errors': errors
        }), 400
    
    # Build query
    query = Token.query
    
    if status:
        query = query.filter_by(status=status)
    
    if date:
        from datetime import datetime
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Token.generated_at) == date_obj)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }), 400
    
    tokens = query.order_by(Token.generated_at.desc()).paginate(
        page=page, per_page=limit, error_out=False
    )
    
    return jsonify({
        'status': 'success',
        'tokens': [token.to_dict() for token in tokens.items],
        'pagination': get_pagination_info(page, limit, tokens.total)
    })

@staff_bp.route('/token/<int:token_id>/status', methods=['PUT'])
@api_login_required
@api_role_required('staff')
@validate_json_content_type
@handle_errors
def update_token_status_endpoint(token_id):
    """Update token status"""
    data = request.get_json()
    
    status = data.get('status')
    counter_number = data.get('counter_number')
    notes = data.get('notes')
    
    if not status:
        return jsonify({
            'status': 'error',
            'message': 'Status is required'
        }), 400
    
    # Update token status
    updated_token = update_token_status(
        token_id, status, counter_number, notes, current_user
    )
    
    if not updated_token:
        return jsonify({
            'status': 'error',
            'message': 'Token not found'
        }), 404
    
    # Emit WebSocket events
    emit('token_updated', {
        'token': updated_token.to_dict()
    }, room='staff')
    
    emit('token_updated', {
        'token': updated_token.to_dict()
    }, room='admin')
    
    # Emit to specific customer
    emit('token_updated', {
        'token': updated_token.to_dict()
    }, room=f'customer_{updated_token.customer_id}')
    
    return jsonify({
        'status': 'success',
        'message': 'Token status updated successfully',
        'token': updated_token.to_dict()
    })

@staff_bp.route('/token/<int:token_id>/call', methods=['PUT'])
@api_login_required
@api_role_required('staff')
@handle_errors
def call_token(token_id):
    """Call a specific token"""
    data = request.get_json()
    counter_number = data.get('counter_number', 'Counter 1')
    
    # Update token to in_progress
    updated_token = update_token_status(
        token_id, 'in_progress', counter_number, served_by=current_user
    )
    
    if not updated_token:
        return jsonify({
            'status': 'error',
            'message': 'Token not found'
        }), 404
    
    # Emit WebSocket events
    emit('token_called', {
        'token_number': updated_token.token_number,
        'counter_number': counter_number,
        'message': f'Token {updated_token.token_number} called to {counter_number}'
    }, room=f'customer_{updated_token.customer_id}')
    
    emit('token_updated', {
        'token': updated_token.to_dict()
    }, room='staff')
    
    emit('token_updated', {
        'token': updated_token.to_dict()
    }, room='admin')
    
    return jsonify({
        'status': 'success',
        'message': f'Token {updated_token.token_number} called to {counter_number}',
        'token': updated_token.to_dict()
    })

@staff_bp.route('/token/next', methods=['POST'])
@api_login_required
@api_role_required('staff')
@validate_json_content_type
@handle_errors
def call_next_token_endpoint():
    """Call next token in queue"""
    data = request.get_json()
    counter_number = data.get('counter_number', 'Counter 1')
    
    # Call next token
    result = call_next_token(counter_number, current_user)
    
    if result['status'] == 'error':
        return jsonify(result), 400
    
    # Emit WebSocket events
    token = result['token']
    emit('token_called', {
        'token_number': token['token_number'],
        'counter_number': counter_number,
        'message': f'Token {token["token_number"]} called to {counter_number}'
    }, room=f'customer_{token["customer_id"]}')
    
    emit('token_updated', {
        'token': token
    }, room='staff')
    
    emit('token_updated', {
        'token': token
    }, room='admin')
    
    return jsonify(result)

@staff_bp.route('/token/<int:token_id>/complete', methods=['PUT'])
@api_login_required
@api_role_required('staff')
@handle_errors
def complete_token_endpoint(token_id):
    """Complete a token"""
    result = complete_token(token_id, current_user)
    
    if result['status'] == 'error':
        return jsonify(result), 400
    
    # Emit WebSocket events
    token = result['token']
    emit('token_updated', {
        'token': token
    }, room='staff')
    
    emit('token_updated', {
        'token': token
    }, room='admin')
    
    emit('token_updated', {
        'token': token
    }, room=f'customer_{token["customer_id"]}')
    
    return jsonify(result)

@staff_bp.route('/token/<int:token_id>', methods=['GET'])
@api_login_required
@api_role_required('staff')
@handle_errors
def get_token_details(token_id):
    """Get token details"""
    token = get_token_by_id(token_id)
    
    if not token:
        return jsonify({
            'status': 'error',
            'message': 'Token not found'
        }), 404
    
    return jsonify({
        'status': 'success',
        'token': token.to_dict()
    })

@staff_bp.route('/atm/<int:atm_id>', methods=['PUT'])
@api_login_required
@api_role_required('staff')
@validate_json_content_type
@handle_errors
def update_atm_status_endpoint(atm_id):
    """Update ATM status"""
    data = request.get_json()
    
    # Validate ATM data
    errors = validate_atm_data(data)
    if errors:
        return jsonify({
            'status': 'error',
            'message': 'Validation errors',
            'errors': errors
        }), 400
    
    status = data.get('status')
    queue_length = data.get('queue_length')
    cash_available = data.get('cash_available')
    notes = data.get('notes')
    
    # Update ATM status
    result = update_atm_status(
        atm_id, status, queue_length, cash_available, notes, current_user
    )
    
    if result['status'] == 'error':
        return jsonify(result), 404
    
    return jsonify(result)

@staff_bp.route('/atm-status', methods=['GET'])
@api_login_required
@api_role_required('staff')
@handle_errors
def get_atm_status():
    """Get ATM status"""
    atm_status = get_all_atm_status()
    
    return jsonify({
        'status': 'success',
        'atms': [atm.to_dict() for atm in atm_status]
    })

@staff_bp.route('/analytics', methods=['GET'])
@api_login_required
@api_role_required('staff')
@handle_errors
def get_staff_analytics():
    """Get staff analytics"""
    days = request.args.get('days', 30, type=int)
    
    # Get staff performance
    performance = get_staff_performance(days)
    
    # Get token statistics
    stats = get_token_statistics()
    
    return jsonify({
        'status': 'success',
        'performance': performance,
        'statistics': stats
    })
