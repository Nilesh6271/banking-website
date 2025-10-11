from database import db
from database.models import ATMStatus
from flask_socketio import emit
from datetime import datetime

def get_all_atm_status():
    """Get all ATM status records"""
    return ATMStatus.query.order_by(ATMStatus.atm_name).all()

def get_atm_by_id(atm_id):
    """Get ATM by ID"""
    return ATMStatus.query.get(atm_id)

def update_atm_status(atm_id, status, queue_length=None, cash_available=None, notes=None, updated_by=None):
    """Update ATM status"""
    atm = get_atm_by_id(atm_id)
    
    if not atm:
        return {
            'status': 'error',
            'message': 'ATM not found'
        }
    
    # Update fields
    atm.status = status
    atm.last_updated = datetime.utcnow()
    atm.updated_by = updated_by.user_id if updated_by else None
    
    if queue_length is not None:
        atm.queue_length = queue_length
    
    if cash_available is not None:
        atm.cash_available = cash_available
    
    if notes:
        atm.notes = notes
    
    db.session.commit()
    
    # Emit WebSocket event
    emit('atm_status_updated', {
        'atm': atm.to_dict()
    }, broadcast=True)
    
    return {
        'status': 'success',
        'message': 'ATM status updated successfully',
        'atm': atm.to_dict()
    }

def create_atm(atm_name, location, status='operational'):
    """Create new ATM"""
    atm = ATMStatus(
        atm_name=atm_name,
        location=location,
        status=status
    )
    
    db.session.add(atm)
    db.session.commit()
    
    return {
        'status': 'success',
        'message': 'ATM created successfully',
        'atm': atm.to_dict()
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

def get_atm_uptime_percentage(atm_id, days=30):
    """Calculate ATM uptime percentage"""
    from datetime import timedelta
    
    atm = get_atm_by_id(atm_id)
    if not atm:
        return 0
    
    # This is a simplified calculation
    # In a real system, you'd track status changes over time
    if atm.status == 'operational':
        return 100.0
    else:
        return 0.0

def get_atm_queue_trends(atm_id, days=7):
    """Get ATM queue trends"""
    # This would require additional tracking in a real system
    # For now, return current queue length
    atm = get_atm_by_id(atm_id)
    if not atm:
        return []
    
    return [{
        'date': datetime.now().date().isoformat(),
        'queue_length': atm.queue_length
    }]

def initialize_default_atms():
    """Initialize default ATM records"""
    if ATMStatus.query.count() == 0:
        default_atms = [
            ATMStatus(
                atm_name='ATM-01',
                location='Main Branch Lobby',
                status='operational',
                queue_length=0,
                cash_available=True
            ),
            ATMStatus(
                atm_name='ATM-02',
                location='Branch Exterior',
                status='operational',
                queue_length=0,
                cash_available=True
            ),
            ATMStatus(
                atm_name='ATM-03',
                location='Shopping Mall Branch',
                status='operational',
                queue_length=0,
                cash_available=True
            )
        ]
        
        for atm in default_atms:
            db.session.add(atm)
        
        db.session.commit()
        return True
    
    return False

def get_atm_by_name(atm_name):
    """Get ATM by name"""
    return ATMStatus.query.filter_by(atm_name=atm_name).first()

def update_atm_queue(atm_id, queue_length):
    """Update ATM queue length"""
    atm = get_atm_by_id(atm_id)
    
    if not atm:
        return {
            'status': 'error',
            'message': 'ATM not found'
        }
    
    atm.queue_length = max(0, queue_length)  # Ensure non-negative
    atm.last_updated = datetime.utcnow()
    
    db.session.commit()
    
    # Emit WebSocket event
    emit('atm_status_updated', {
        'atm': atm.to_dict()
    }, broadcast=True)
    
    return {
        'status': 'success',
        'message': 'ATM queue updated successfully',
        'atm': atm.to_dict()
    }

def get_atm_status_summary():
    """Get summary of all ATM statuses"""
    atms = get_all_atm_status()
    
    summary = {
        'total_atms': len(atms),
        'operational': 0,
        'out_of_service': 0,
        'low_cash': 0,
        'under_maintenance': 0,
        'total_queue': 0,
        'atms_with_cash': 0
    }
    
    for atm in atms:
        summary[atm.status] += 1
        summary['total_queue'] += atm.queue_length
        
        if atm.cash_available:
            summary['atms_with_cash'] += 1
    
    return summary
