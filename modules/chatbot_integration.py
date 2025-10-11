import sys
import os
import json
from datetime import datetime
from database.models import ChatLog, ChatbotFAQ, db
from config import Config

# Global chatbot instance
chatbot_instance = None

def initialize_chatbot(excel_path):
    """Initialize chatbot with Excel data"""
    global chatbot_instance
    
    try:
        # Check if Excel file exists
        if not os.path.exists(excel_path):
            print(f"Excel file not found: {excel_path}")
            return False
        
        # Import chatbot data into database
        import_chatbot_data(excel_path)
        
        print("✓ Chatbot initialized successfully")
        return True
        
    except Exception as e:
        print(f"✗ Chatbot initialization failed: {str(e)}")
        return False

def import_chatbot_data(excel_path):
    """Import chatbot data from Excel into database"""
    try:
        import pandas as pd
        
        # Clear existing data
        ChatbotFAQ.query.delete()
        db.session.commit()
        
        # Define sheets to import
        sheets = ['Definitions', 'DepositRates', 'LoanRates', 'BankInfo', 'Forms']
        
        for sheet in sheets:
            try:
                df = pd.read_excel(excel_path, sheet_name=sheet)
                
                for _, row in df.iterrows():
                    # Skip empty rows
                    if row.isnull().all():
                        continue
                    
                    faq = ChatbotFAQ(
                        sheet_name=sheet,
                        category=sheet,
                        data_json=json.dumps(row.to_dict(), default=str)
                    )
                    db.session.add(faq)
                
                print(f"✓ Imported {sheet} data")
                
            except Exception as e:
                print(f"✗ Error importing {sheet}: {str(e)}")
        
        db.session.commit()
        print("✓ Chatbot data imported successfully")
        
    except Exception as e:
        print(f"✗ Error importing chatbot data: {str(e)}")
        raise

def get_chatbot_response(query, user_id=None, session_id=None):
    """
    Get chatbot response based on query
    This is a simplified implementation - you can integrate your existing chatbot here
    """
    try:
        # Clean query
        query = query.strip().lower()
        
        # Search in FAQ data
        faq_results = search_faq_data(query)
        
        if faq_results:
            # Return best match
            best_match = faq_results[0]
            response = format_faq_response(best_match)
            confidence = 0.8
            response_type = 'faq'
        else:
            # Default response
            response = "I'm sorry, I couldn't find specific information about that. Please contact our customer service for assistance."
            confidence = 0.1
            response_type = 'default'
        
        # Log conversation
        log_entry = ChatLog(
            customer_id=user_id,
            session_id=session_id or 'anonymous',
            query=query,
            response=response,
            confidence=confidence,
            response_type=response_type,
            timestamp=datetime.utcnow()
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return {
            'response': response,
            'confidence': confidence,
            'type': response_type,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Chatbot error: {str(e)}")
        return {
            'response': "I'm having trouble processing your request. Please contact customer support.",
            'confidence': 0.0,
            'type': 'error',
            'timestamp': datetime.now().isoformat()
        }

def search_faq_data(query):
    """Search FAQ data for relevant information"""
    try:
        # Simple keyword matching
        keywords = query.split()
        
        # Search in all FAQ entries
        faq_entries = ChatbotFAQ.query.all()
        matches = []
        
        for entry in faq_entries:
            try:
                data = json.loads(entry.data_json)
                match_score = 0
                
                # Check for keyword matches in data
                for key, value in data.items():
                    if value and isinstance(value, str):
                        value_lower = value.lower()
                        for keyword in keywords:
                            if keyword in value_lower:
                                match_score += 1
                
                if match_score > 0:
                    matches.append({
                        'entry': entry,
                        'data': data,
                        'score': match_score
                    })
            
            except json.JSONDecodeError:
                continue
        
        # Sort by match score
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        return matches
        
    except Exception as e:
        print(f"Error searching FAQ data: {str(e)}")
        return []

def format_faq_response(match):
    """Format FAQ response"""
    try:
        data = match['data']
        sheet_name = match['entry'].sheet_name
        
        # Format response based on sheet type
        if sheet_name == 'Definitions':
            return format_definition_response(data)
        elif sheet_name == 'DepositRates':
            return format_deposit_rates_response(data)
        elif sheet_name == 'LoanRates':
            return format_loan_rates_response(data)
        elif sheet_name == 'BankInfo':
            return format_bank_info_response(data)
        elif sheet_name == 'Forms':
            return format_forms_response(data)
        else:
            return format_generic_response(data)
            
    except Exception as e:
        print(f"Error formatting response: {str(e)}")
        return "I found some information, but I'm having trouble formatting it. Please contact customer service for details."

def format_definition_response(data):
    """Format definition response"""
    if 'Term' in data and 'Definition' in data:
        return f"**{data['Term']}**: {data['Definition']}"
    return format_generic_response(data)

def format_deposit_rates_response(data):
    """Format deposit rates response"""
    if 'Account Type' in data and 'Interest Rate' in data:
        return f"**{data['Account Type']}**: {data['Interest Rate']}"
    return format_generic_response(data)

def format_loan_rates_response(data):
    """Format loan rates response"""
    if 'Loan Type' in data and 'Interest Rate' in data:
        return f"**{data['Loan Type']}**: {data['Interest Rate']}"
    return format_generic_response(data)

def format_bank_info_response(data):
    """Format bank info response"""
    if 'Information' in data and 'Details' in data:
        return f"**{data['Information']}**: {data['Details']}"
    return format_generic_response(data)

def format_forms_response(data):
    """Format forms response"""
    if 'Form Name' in data and 'Description' in data:
        return f"**{data['Form Name']}**: {data['Description']}"
    return format_generic_response(data)

def format_generic_response(data):
    """Format generic response"""
    response_parts = []
    for key, value in data.items():
        if value and str(value).strip():
            response_parts.append(f"**{key}**: {value}")
    
    return "\n".join(response_parts) if response_parts else "I found some information, but it's not in a standard format."

def get_chat_history(user_id=None, session_id=None, limit=50):
    """Get chat history"""
    query = ChatLog.query
    
    if user_id:
        query = query.filter_by(customer_id=user_id)
    elif session_id:
        query = query.filter_by(session_id=session_id)
    
    return query.order_by(ChatLog.timestamp.desc()).limit(limit).all()

def update_chatbot_data(excel_path=None):
    """Reload chatbot data from Excel"""
    if excel_path is None:
        excel_path = Config.CHATBOT_EXCEL_PATH
    
    return initialize_chatbot(excel_path)

def get_chatbot_statistics():
    """Get chatbot usage statistics"""
    total_queries = ChatLog.query.count()
    high_confidence_queries = ChatLog.query.filter(
        ChatLog.confidence >= 0.7
    ).count()
    
    # Most common queries
    common_queries = db.session.query(
        ChatLog.query,
        db.func.count(ChatLog.log_id).label('count')
    ).group_by(ChatLog.query).order_by(
        db.func.count(ChatLog.log_id).desc()
    ).limit(10).all()
    
    return {
        'total_queries': total_queries,
        'high_confidence_responses': high_confidence_queries,
        'confidence_rate': (high_confidence_queries / total_queries * 100) if total_queries > 0 else 0,
        'common_queries': [
            {'query': record.query, 'count': record.count}
            for record in common_queries
        ]
    }
