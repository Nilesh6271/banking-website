from flask_socketio import emit, join_room, leave_room, disconnect
from flask_login import current_user
from datetime import datetime
import logging

def register_socketio_events(socketio):
    """Register all SocketIO event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        if current_user.is_authenticated:
            # Join user-specific room
            user_room = f"{current_user.role}_{current_user.user_id}"
            join_room(user_room)
            
            # Join role-based room
            join_room(current_user.role)
            
            # Join admin room if user is admin
            if current_user.role == 'admin':
                join_room('admin')
            
            # Join staff room if user is staff or admin
            if current_user.role in ['staff', 'admin']:
                join_room('staff')
            
            emit('connected', {
                'message': 'Connected successfully',
                'user': current_user.to_dict(),
                'timestamp': datetime.now().isoformat()
            })
            
            logging.info(f"User {current_user.username} connected to WebSocket")
        else:
            # Anonymous connection
            emit('connected', {
                'message': 'Connected as anonymous user',
                'timestamp': datetime.now().isoformat()
            })
            logging.info("Anonymous user connected to WebSocket")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        if current_user.is_authenticated:
            # Leave user-specific room
            user_room = f"{current_user.role}_{current_user.user_id}"
            leave_room(user_room)
            
            # Leave role-based room
            leave_room(current_user.role)
            
            # Leave admin room if user is admin
            if current_user.role == 'admin':
                leave_room('admin')
            
            # Leave staff room if user is staff or admin
            if current_user.role in ['staff', 'admin']:
                leave_room('staff')
            
            logging.info(f"User {current_user.username} disconnected from WebSocket")
        else:
            logging.info("Anonymous user disconnected from WebSocket")
    
    @socketio.on('join_room')
    def handle_join_room(data):
        """Handle joining specific room"""
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        room = data.get('room')
        if not room:
            emit('error', {'message': 'Room name required'})
            return
        
        # Validate room access
        if room == 'admin' and current_user.role != 'admin':
            emit('error', {'message': 'Access denied'})
            return
        
        if room == 'staff' and current_user.role not in ['staff', 'admin']:
            emit('error', {'message': 'Access denied'})
            return
        
        if room.startswith('customer_') and current_user.role != 'customer':
            emit('error', {'message': 'Access denied'})
            return
        
        join_room(room)
        emit('joined_room', {
            'room': room,
            'message': f'Joined room {room}'
        })
        
        logging.info(f"User {current_user.username} joined room {room}")
    
    @socketio.on('leave_room')
    def handle_leave_room(data):
        """Handle leaving specific room"""
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        room = data.get('room')
        if not room:
            emit('error', {'message': 'Room name required'})
            return
        
        leave_room(room)
        emit('left_room', {
            'room': room,
            'message': f'Left room {room}'
        })
        
        logging.info(f"User {current_user.username} left room {room}")
    
    @socketio.on('ping')
    def handle_ping():
        """Handle ping for connection testing"""
        emit('pong', {
            'timestamp': datetime.now().isoformat(),
            'message': 'pong'
        })
    
    @socketio.on('get_status')
    def handle_get_status():
        """Handle status request"""
        if current_user.is_authenticated:
            emit('status', {
                'authenticated': True,
                'user': current_user.to_dict(),
                'timestamp': datetime.now().isoformat()
            })
        else:
            emit('status', {
                'authenticated': False,
                'timestamp': datetime.now().isoformat()
            })
    
    @socketio.on('subscribe_notifications')
    def handle_subscribe_notifications():
        """Handle notification subscription"""
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        # Join notification room based on user role
        if current_user.role == 'admin':
            join_room('admin_notifications')
        elif current_user.role == 'staff':
            join_room('staff_notifications')
        elif current_user.role == 'customer':
            join_room(f'customer_notifications_{current_user.user_id}')
        
        emit('subscribed', {
            'message': 'Subscribed to notifications',
            'timestamp': datetime.now().isoformat()
        })
        
        logging.info(f"User {current_user.username} subscribed to notifications")
    
    @socketio.on('unsubscribe_notifications')
    def handle_unsubscribe_notifications():
        """Handle notification unsubscription"""
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        # Leave notification room based on user role
        if current_user.role == 'admin':
            leave_room('admin_notifications')
        elif current_user.role == 'staff':
            leave_room('staff_notifications')
        elif current_user.role == 'customer':
            leave_room(f'customer_notifications_{current_user.user_id}')
        
        emit('unsubscribed', {
            'message': 'Unsubscribed from notifications',
            'timestamp': datetime.now().isoformat()
        })
        
        logging.info(f"User {current_user.username} unsubscribed from notifications")
    
    @socketio.on('error')
    def handle_error(data):
        """Handle client errors"""
        logging.error(f"Client error: {data}")
        emit('error_received', {
            'message': 'Error received and logged',
            'timestamp': datetime.now().isoformat()
        })
    
    # Custom event handlers for specific business logic
    @socketio.on('request_token_update')
    def handle_request_token_update(data):
        """Handle token update requests"""
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        token_id = data.get('token_id')
        if not token_id:
            emit('error', {'message': 'Token ID required'})
            return
        
        # Emit current token status
        from database.models import Token
        token = Token.query.get(token_id)
        if token:
            emit('token_update', {
                'token': token.to_dict(),
                'timestamp': datetime.now().isoformat()
            })
        else:
            emit('error', {'message': 'Token not found'})
    
    @socketio.on('request_atm_status')
    def handle_request_atm_status():
        """Handle ATM status requests"""
        from modules.atm_manager import get_all_atm_status
        
        atm_status = get_all_atm_status()
        emit('atm_status_update', {
            'atms': [atm.to_dict() for atm in atm_status],
            'timestamp': datetime.now().isoformat()
        })
    
    @socketio.on('request_dashboard_data')
    def handle_request_dashboard_data():
        """Handle dashboard data requests"""
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        from modules.analytics import get_dashboard_statistics
        
        stats = get_dashboard_statistics()
        emit('dashboard_data', {
            'statistics': stats,
            'timestamp': datetime.now().isoformat()
        })
