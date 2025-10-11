from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship

# Import db from this module (not from app.py)
from . import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'admin', 'staff', 'customer'
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(15), nullable=False)
    account_number = Column(String(20), unique=True, nullable=True)  # Only for customers
    status = Column(String(20), default='active')  # 'active', 'inactive', 'suspended'
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    # Relationships
    tokens = relationship('Token', backref='customer', lazy='dynamic', foreign_keys='Token.customer_id')
    created_users = relationship('User', backref='creator', remote_side=[user_id])
    
    def get_id(self):
        return str(self.user_id)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'role': self.role,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'account_number': self.account_number,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class Token(db.Model):
    __tablename__ = 'tokens'
    
    token_id = Column(Integer, primary_key=True, autoincrement=True)
    token_number = Column(String(20), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    service_type = Column(String(50), nullable=False)  # 'cash_deposit', 'general_query', 'loan_application', 'meet_gm'
    priority = Column(String(20), default='normal')  # 'normal', 'senior_citizen', 'vip'
    status = Column(String(20), default='waiting', index=True)  # 'waiting', 'in_progress', 'completed', 'cancelled'
    counter_number = Column(String(10), nullable=True)
    estimated_wait_time = Column(Integer, nullable=True)  # in minutes
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    called_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    served_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    # Relationships
    staff_member = relationship('User', foreign_keys=[served_by], backref='served_tokens')
    
    def to_dict(self):
        return {
            'token_id': self.token_id,
            'token_number': self.token_number,
            'customer_id': self.customer_id,
            'service_type': self.service_type,
            'priority': self.priority,
            'status': self.status,
            'counter_number': self.counter_number,
            'estimated_wait_time': self.estimated_wait_time,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'called_at': self.called_at.isoformat() if self.called_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'notes': self.notes,
            'served_by': self.served_by,
            'customer_name': self.customer.full_name if self.customer else None,
            'staff_name': self.staff_member.full_name if self.staff_member else None
        }

class ATMStatus(db.Model):
    __tablename__ = 'atm_status'
    
    atm_id = Column(Integer, primary_key=True, autoincrement=True)
    atm_name = Column(String(100), nullable=False)
    location = Column(String(200), nullable=False)
    status = Column(String(20), default='operational')  # 'operational', 'out_of_service', 'low_cash', 'under_maintenance'
    queue_length = Column(Integer, default=0)
    cash_available = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    updater = relationship('User', foreign_keys=[updated_by])
    
    def to_dict(self):
        return {
            'atm_id': self.atm_id,
            'atm_name': self.atm_name,
            'location': self.location,
            'status': self.status,
            'queue_length': self.queue_length,
            'cash_available': self.cash_available,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'updated_by': self.updated_by,
            'notes': self.notes,
            'updater_name': self.updater.full_name if self.updater else None
        }

class ChatbotFAQ(db.Model):
    __tablename__ = 'chatbot_faq'
    
    faq_id = Column(Integer, primary_key=True, autoincrement=True)
    sheet_name = Column(String(50), nullable=False)  # 'Definitions', 'DepositRates', etc.
    category = Column(String(50), nullable=True)
    data_json = Column(Text, nullable=False)  # JSON string of row data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'faq_id': self.faq_id,
            'sheet_name': self.sheet_name,
            'category': self.category,
            'data_json': self.data_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ChatLog(db.Model):
    __tablename__ = 'chat_logs'
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    session_id = Column(String(50), nullable=False)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    response_type = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship('User', foreign_keys=[customer_id])
    
    def to_dict(self):
        return {
            'log_id': self.log_id,
            'customer_id': self.customer_id,
            'session_id': self.session_id,
            'query': self.query,
            'response': self.response,
            'confidence': self.confidence,
            'response_type': self.response_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'customer_name': self.user.full_name if self.user else None
        }

class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    action = Column(String(100), nullable=False)  # 'login', 'logout', 'token_generated', 'user_created', etc.
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship('User', foreign_keys=[user_id])
    
    def to_dict(self):
        return {
            'log_id': self.log_id,
            'user_id': self.user_id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user_name': self.user.full_name if self.user else None
        }
