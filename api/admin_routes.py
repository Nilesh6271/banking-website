from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from modules.user_manager import (
    get_all_users, create_user, update_user, delete_user, reset_user_password,
    get_user_statistics, get_recent_users, search_users
)
from modules.analytics import get_comprehensive_analytics, get_dashboard_statistics
from modules.chatbot_integration import update_chatbot_data, get_chatbot_statistics
from utils.decorators import admin_required, validate_json_content_type, handle_errors
from utils.validators import validate_user_data, validate_pagination_params
from utils.helpers import get_pagination_info
from database.models import SystemLog, db
from flask_socketio import emit

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@login_required
@admin_required
@handle_errors
def admin_dashboard():
    """Get comprehensive admin dashboard data"""
    # Get dashboard statistics
    stats = get_dashboard_statistics()
    
    # Get comprehensive analytics
    analytics = get_comprehensive_analytics(days=30)
    
    return jsonify({
        'status': 'success',
        'statistics': stats,
        'analytics': analytics
    })

@admin_bp.route('/users', methods=['GET'])
@login_required
@admin_required
@handle_errors
def get_users():
    """Get all users with filtering and pagination"""
    # Get query parameters
    role = request.args.get('role')
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search = request.args.get('search')
    
    # Validate pagination
    errors = validate_pagination_params(request.args)
    if errors:
        return jsonify({
            'status': 'error',
            'message': 'Invalid pagination parameters',
            'errors': errors
        }), 400
    
    # Get users
    if search:
        users = search_users(search, role)
        total = len(users)
        users = users[(page-1)*limit:page*limit]
    else:
        users_paginated = get_all_users(role, status, page, limit)
        users = users_paginated.items
        total = users_paginated.total
    
    return jsonify({
        'status': 'success',
        'users': [user.to_dict() for user in users],
        'pagination': get_pagination_info(page, limit, total)
    })

@admin_bp.route('/users', methods=['POST'])
@login_required
@admin_required
@validate_json_content_type
@handle_errors
def create_user_endpoint():
    """Create new user"""
    data = request.get_json()
    
    # Validate user data
    errors = validate_user_data(data)
    if errors:
        return jsonify({
            'status': 'error',
            'message': 'Validation errors',
            'errors': errors
        }), 400
    
    # Create user
    result = create_user(data, current_user)
    
    if result['status'] == 'error':
        return jsonify(result), 400
    
    # Emit WebSocket event
    emit('user_created', {
        'user': result['user']
    }, room='admin')
    
    return jsonify(result)

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
@validate_json_content_type
@handle_errors
def update_user_endpoint(user_id):
    """Update user"""
    data = request.get_json()
    
    # Validate user data for update
    errors = validate_user_data(data, is_update=True)
    if errors:
        return jsonify({
            'status': 'error',
            'message': 'Validation errors',
            'errors': errors
        }), 400
    
    # Update user
    result = update_user(user_id, data, current_user)
    
    if result['status'] == 'error':
        return jsonify(result), 404
    
    # Emit WebSocket event
    emit('user_updated', {
        'user': result['user']
    }, room='admin')
    
    return jsonify(result)

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
@handle_errors
def delete_user_endpoint(user_id):
    """Delete user (soft delete)"""
    result = delete_user(user_id, current_user)
    
    if result['status'] == 'error':
        return jsonify(result), 404
    
    return jsonify(result)

@admin_bp.route('/users/<int:user_id>/reset-password', methods=['PUT'])
@login_required
@admin_required
@validate_json_content_type
@handle_errors
def reset_user_password_endpoint(user_id):
    """Reset user password"""
    data = request.get_json()
    
    new_password = data.get('new_password')
    if not new_password:
        return jsonify({
            'status': 'error',
            'message': 'New password is required'
        }), 400
    
    # Reset password
    result = reset_user_password(user_id, new_password, current_user)
    
    if result['status'] == 'error':
        return jsonify(result), 404
    
    return jsonify(result)

@admin_bp.route('/analytics', methods=['GET'])
@login_required
@admin_required
@handle_errors
def get_analytics():
    """Get comprehensive analytics"""
    days = request.args.get('days', 30, type=int)
    analytics_type = request.args.get('type', 'all')
    
    if analytics_type == 'all':
        analytics = get_comprehensive_analytics(days)
    else:
        # Return specific analytics type
        analytics = get_comprehensive_analytics(days)
        if analytics_type in analytics:
            analytics = {analytics_type: analytics[analytics_type]}
    
    return jsonify({
        'status': 'success',
        'analytics': analytics
    })

@admin_bp.route('/analytics/tokens', methods=['GET'])
@login_required
@admin_required
@handle_errors
def get_token_analytics():
    """Get token analytics"""
    from modules.analytics import get_token_trends
    
    days = request.args.get('days', 30, type=int)
    trends = get_token_trends(days)
    
    return jsonify({
        'status': 'success',
        'trends': trends
    })

@admin_bp.route('/analytics/performance', methods=['GET'])
@login_required
@admin_required
@handle_errors
def get_performance_analytics():
    """Get staff performance analytics"""
    from modules.analytics import get_staff_performance
    
    days = request.args.get('days', 30, type=int)
    performance = get_staff_performance(days)
    
    return jsonify({
        'status': 'success',
        'performance': performance
    })

@admin_bp.route('/system-logs', methods=['GET'])
@login_required
@admin_required
@handle_errors
def get_system_logs():
    """Get system logs"""
    # Get query parameters
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    # Validate pagination
    errors = validate_pagination_params(request.args)
    if errors:
        return jsonify({
            'status': 'error',
            'message': 'Invalid pagination parameters',
            'errors': errors
        }), 400
    
    # Build query
    query = SystemLog.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if action:
        query = query.filter_by(action=action)
    
    if start_date:
        from datetime import datetime
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(SystemLog.timestamp) >= start_date_obj)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid start_date format. Use YYYY-MM-DD'
            }), 400
    
    if end_date:
        from datetime import datetime
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(SystemLog.timestamp) <= end_date_obj)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid end_date format. Use YYYY-MM-DD'
            }), 400
    
    logs = query.order_by(SystemLog.timestamp.desc()).paginate(
        page=page, per_page=limit, error_out=False
    )
    
    return jsonify({
        'status': 'success',
        'logs': [log.to_dict() for log in logs.items],
        'pagination': get_pagination_info(page, limit, logs.total)
    })

@admin_bp.route('/chatbot-data', methods=['PUT'])
@login_required
@admin_required
@validate_json_content_type
@handle_errors
def update_chatbot_data_endpoint():
    """Update chatbot FAQ data"""
    data = request.get_json()
    
    sheet_name = data.get('sheet_name')
    faq_id = data.get('faq_id')
    new_data = data.get('data')
    
    if not all([sheet_name, faq_id, new_data]):
        return jsonify({
            'status': 'error',
            'message': 'sheet_name, faq_id, and data are required'
        }), 400
    
    # Update FAQ data
    from database.models import ChatbotFAQ
    faq = ChatbotFAQ.query.get(faq_id)
    
    if not faq:
        return jsonify({
            'status': 'error',
            'message': 'FAQ not found'
        }), 404
    
    faq.data_json = json.dumps(new_data, default=str)
    faq.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Chatbot data updated successfully'
    })

@admin_bp.route('/chatbot-data/reload', methods=['POST'])
@login_required
@admin_required
@handle_errors
def reload_chatbot_data():
    """Reload chatbot data from Excel"""
    result = update_chatbot_data()
    
    if result:
        return jsonify({
            'status': 'success',
            'message': 'Chatbot data reloaded successfully'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Failed to reload chatbot data'
        }), 500

@admin_bp.route('/chatbot/statistics', methods=['GET'])
@login_required
@admin_required
@handle_errors
def get_chatbot_statistics_endpoint():
    """Get chatbot statistics"""
    stats = get_chatbot_statistics()
    
    return jsonify({
        'status': 'success',
        'statistics': stats
    })
