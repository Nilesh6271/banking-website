from flask import Blueprint, request, jsonify
from flask_login import current_user
from modules.chatbot_integration import get_chatbot_response, get_chat_history
from utils.decorators import validate_json_content_type, handle_errors
from utils.validators import validate_required_fields
import uuid

chatbot_bp = Blueprint('chatbot', __name__)

@chatbot_bp.route('/query', methods=['POST'])
@validate_json_content_type
@handle_errors
def chat_query():
    """
    Handle chatbot queries
    Can be called without authentication (for public queries)
    Or with authentication (for logged-in users)
    """
    data = request.get_json()
    
    # Validate required fields
    missing_fields = validate_required_fields(data, ['message'])
    if missing_fields:
        return jsonify({
            'status': 'error',
            'message': f'Missing required fields: {", ".join(missing_fields)}'
        }), 400
    
    message = data.get('message', '').strip()
    session_id = data.get('session_id', str(uuid.uuid4()))
    
    if not message:
        return jsonify({
            'status': 'error',
            'message': 'Message cannot be empty'
        }), 400
    
    # Get user_id if authenticated
    user_id = current_user.user_id if current_user.is_authenticated else None
    
    # Get response from chatbot
    result = get_chatbot_response(message, user_id, session_id)
    
    return jsonify({
        'status': 'success',
        **result
    })

@chatbot_bp.route('/history', methods=['GET'])
@handle_errors
def chat_history():
    """Get chat history for authenticated user or session"""
    # Get session ID from query parameters
    session_id = request.args.get('session_id')
    
    if current_user.is_authenticated:
        # Get history for authenticated user
        history = get_chat_history(user_id=current_user.user_id, limit=50)
    elif session_id:
        # Get history for session
        history = get_chat_history(session_id=session_id, limit=50)
    else:
        return jsonify({
            'status': 'error',
            'message': 'Authentication required or session_id must be provided'
        }), 401
    
    return jsonify({
        'status': 'success',
        'messages': [log.to_dict() for log in history]
    })

@chatbot_bp.route('/session', methods=['POST'])
@handle_errors
def create_session():
    """Create new chat session"""
    session_id = str(uuid.uuid4())
    
    return jsonify({
        'status': 'success',
        'session_id': session_id,
        'message': 'Chat session created'
    })

@chatbot_bp.route('/feedback', methods=['POST'])
@validate_json_content_type
@handle_errors
def submit_feedback():
    """Submit feedback for chatbot response"""
    data = request.get_json()
    
    # Validate required fields
    missing_fields = validate_required_fields(data, ['session_id', 'response_id', 'rating'])
    if missing_fields:
        return jsonify({
            'status': 'error',
            'message': f'Missing required fields: {", ".join(missing_fields)}'
        }), 400
    
    session_id = data.get('session_id')
    response_id = data.get('response_id')
    rating = data.get('rating')  # 1-5 scale
    feedback = data.get('feedback', '')
    
    # Validate rating
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({
            'status': 'error',
            'message': 'Rating must be between 1 and 5'
        }), 400
    
    # Log feedback (you can extend this to store in database)
    print(f"Feedback received - Session: {session_id}, Response: {response_id}, Rating: {rating}, Feedback: {feedback}")
    
    return jsonify({
        'status': 'success',
        'message': 'Feedback submitted successfully'
    })

@chatbot_bp.route('/suggestions', methods=['GET'])
@handle_errors
def get_suggestions():
    """Get chatbot suggestions based on common queries"""
    suggestions = [
        "What are the current interest rates?",
        "How do I open a savings account?",
        "What documents are required for a loan?",
        "What are the bank's working hours?",
        "How do I apply for a credit card?",
        "What is the minimum balance for savings account?",
        "How do I transfer money online?",
        "What are the charges for ATM transactions?",
        "How do I update my mobile number?",
        "What is the process for account closure?"
    ]
    
    return jsonify({
        'status': 'success',
        'suggestions': suggestions
    })

@chatbot_bp.route('/status', methods=['GET'])
@handle_errors
def chatbot_status():
    """Get chatbot status and statistics"""
    from modules.chatbot_integration import get_chatbot_statistics
    
    stats = get_chatbot_statistics()
    
    return jsonify({
        'status': 'success',
        'chatbot_status': 'operational',
        'statistics': stats
    })
