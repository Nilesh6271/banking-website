from database.models import Token, User, ATMStatus, SystemLog, db
from datetime import datetime, timedelta
from sqlalchemy import func, extract
from utils.helpers import get_date_range

def get_dashboard_statistics():
    """Get comprehensive dashboard statistics"""
    # User statistics
    user_stats = get_user_statistics()
    
    # Token statistics
    token_stats = get_token_statistics()
    
    # ATM statistics
    atm_stats = get_atm_statistics()
    
    # Recent activity
    recent_activity = get_recent_activity(limit=10)
    
    return {
        'users': user_stats,
        'tokens': token_stats,
        'atms': atm_stats,
        'recent_activity': recent_activity
    }

def get_user_statistics():
    """Get user statistics"""
    total_users = User.query.count()
    admin_users = User.query.filter_by(role='admin').count()
    staff_users = User.query.filter_by(role='staff').count()
    customer_users = User.query.filter_by(role='customer').count()
    active_users = User.query.filter_by(status='active').count()
    
    return {
        'total': total_users,
        'admin': admin_users,
        'staff': staff_users,
        'customer': customer_users,
        'active': active_users
    }

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

def get_atm_statistics():
    """Get ATM statistics"""
    total_atms = ATMStatus.query.count()
    operational_atms = ATMStatus.query.filter_by(status='operational').count()
    out_of_service_atms = ATMStatus.query.filter_by(status='out_of_service').count()
    low_cash_atms = ATMStatus.query.filter_by(status='low_cash').count()
    under_maintenance_atms = ATMStatus.query.filter_by(status='under_maintenance').count()
    
    return {
        'total': total_atms,
        'operational': operational_atms,
        'out_of_service': out_of_service_atms,
        'low_cash': low_cash_atms,
        'under_maintenance': under_maintenance_atms
    }

def get_recent_activity(limit=10):
    """Get recent system activity"""
    return SystemLog.query.order_by(
        SystemLog.timestamp.desc()
    ).limit(limit).all()

def get_token_trends(days=30):
    """Get token generation trends"""
    start_date, end_date = get_date_range(days)
    
    # Daily token counts
    daily_counts = db.session.query(
        func.date(Token.generated_at).label('date'),
        func.count(Token.token_id).label('count')
    ).filter(
        Token.generated_at >= start_date,
        Token.generated_at <= end_date
    ).group_by(
        func.date(Token.generated_at)
    ).order_by('date').all()
    
    # Service type breakdown
    service_breakdown = db.session.query(
        Token.service_type,
        func.count(Token.token_id).label('count')
    ).filter(
        Token.generated_at >= start_date,
        Token.generated_at <= end_date
    ).group_by(Token.service_type).all()
    
    return {
        'daily_counts': [
            {'date': str(record.date), 'count': record.count}
            for record in daily_counts
        ],
        'service_breakdown': {
            record.service_type: record.count
            for record in service_breakdown
        }
    }

def get_staff_performance(days=30):
    """Get staff performance metrics"""
    start_date, end_date = get_date_range(days)
    
    # Tokens handled by each staff member
    staff_performance = db.session.query(
        User.full_name,
        User.user_id,
        func.count(Token.token_id).label('tokens_handled'),
        func.avg(
            func.extract('epoch', Token.completed_at - Token.called_at) / 60
        ).label('avg_service_time')
    ).join(
        Token, User.user_id == Token.served_by
    ).filter(
        Token.generated_at >= start_date,
        Token.generated_at <= end_date,
        Token.status == 'completed'
    ).group_by(
        User.user_id, User.full_name
    ).all()
    
    return [
        {
            'staff_name': record.full_name,
            'staff_id': record.user_id,
            'tokens_handled': record.tokens_handled,
            'avg_service_time': float(record.avg_service_time) if record.avg_service_time else 0
        }
        for record in staff_performance
    ]

def get_peak_hours_analysis(days=30):
    """Get peak hours analysis"""
    start_date, end_date = get_date_range(days)
    
    # Hourly token generation
    hourly_counts = db.session.query(
        extract('hour', Token.generated_at).label('hour'),
        func.count(Token.token_id).label('count')
    ).filter(
        Token.generated_at >= start_date,
        Token.generated_at <= end_date
    ).group_by(
        extract('hour', Token.generated_at)
    ).order_by('hour').all()
    
    return [
        {'hour': record.hour, 'count': record.count}
        for record in hourly_counts
    ]

def get_customer_analytics(days=30):
    """Get customer analytics"""
    start_date, end_date = get_date_range(days)
    
    # Most frequent service types
    service_frequency = db.session.query(
        Token.service_type,
        func.count(Token.token_id).label('count')
    ).filter(
        Token.generated_at >= start_date,
        Token.generated_at <= end_date
    ).group_by(Token.service_type).order_by(
        func.count(Token.token_id).desc()
    ).all()
    
    # Customer visit patterns
    customer_visits = db.session.query(
        User.full_name,
        func.count(Token.token_id).label('visit_count')
    ).join(
        Token, User.user_id == Token.customer_id
    ).filter(
        Token.generated_at >= start_date,
        Token.generated_at <= end_date
    ).group_by(
        User.user_id, User.full_name
    ).order_by(
        func.count(Token.token_id).desc()
    ).limit(10).all()
    
    return {
        'service_frequency': [
            {'service_type': record.service_type, 'count': record.count}
            for record in service_frequency
        ],
        'top_customers': [
            {'customer_name': record.full_name, 'visit_count': record.visit_count}
            for record in customer_visits
        ]
    }

def get_atm_analytics():
    """Get ATM analytics"""
    # ATM uptime percentage
    total_atms = ATMStatus.query.count()
    operational_atms = ATMStatus.query.filter_by(status='operational').count()
    uptime_percentage = (operational_atms / total_atms * 100) if total_atms > 0 else 0
    
    # Queue patterns
    atms_with_queues = ATMStatus.query.filter(ATMStatus.queue_length > 0).count()
    total_queue_length = db.session.query(func.sum(ATMStatus.queue_length)).scalar() or 0
    
    return {
        'uptime_percentage': round(uptime_percentage, 2),
        'atms_with_queues': atms_with_queues,
        'total_queue_length': total_queue_length,
        'avg_queue_length': round(total_queue_length / total_atms, 2) if total_atms > 0 else 0
    }

def get_system_logs_analytics(days=30):
    """Get system logs analytics"""
    start_date, end_date = get_date_range(days)
    
    # Action frequency
    action_counts = db.session.query(
        SystemLog.action,
        func.count(SystemLog.log_id).label('count')
    ).filter(
        SystemLog.timestamp >= start_date,
        SystemLog.timestamp <= end_date
    ).group_by(SystemLog.action).order_by(
        func.count(SystemLog.log_id).desc()
    ).all()
    
    # User activity
    user_activity = db.session.query(
        User.full_name,
        func.count(SystemLog.log_id).label('activity_count')
    ).join(
        SystemLog, User.user_id == SystemLog.user_id
    ).filter(
        SystemLog.timestamp >= start_date,
        SystemLog.timestamp <= end_date
    ).group_by(
        User.user_id, User.full_name
    ).order_by(
        func.count(SystemLog.log_id).desc()
    ).limit(10).all()
    
    return {
        'action_frequency': [
            {'action': record.action, 'count': record.count}
            for record in action_counts
        ],
        'user_activity': [
            {'user_name': record.full_name, 'activity_count': record.activity_count}
            for record in user_activity
        ]
    }

def get_comprehensive_analytics(days=30):
    """Get comprehensive analytics for admin dashboard"""
    return {
        'dashboard_stats': get_dashboard_statistics(),
        'token_trends': get_token_trends(days),
        'staff_performance': get_staff_performance(days),
        'peak_hours': get_peak_hours_analysis(days),
        'customer_analytics': get_customer_analytics(days),
        'atm_analytics': get_atm_analytics(),
        'system_logs': get_system_logs_analytics(days)
    }
