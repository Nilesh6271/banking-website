# Apex Bank Management System

A comprehensive Flask-based server application for bank branch management that runs on an admin laptop and serves customer and staff clients over a local WiFi network.

## Features

- **User Management**: Admin, Staff, and Customer roles with authentication
- **Token System**: Digital token generation and management for bank services
- **ATM Status**: Real-time ATM status tracking and updates
- **AI Chatbot**: Intelligent customer support with Excel data integration
- **Real-time Updates**: WebSocket-based live notifications
- **Analytics Dashboard**: Comprehensive reporting and analytics
- **Network Access**: Serves multiple clients over local WiFi

## Technology Stack

- **Backend**: Flask 3.0+ with SQLAlchemy ORM
- **Database**: SQLite with automatic migrations
- **Real-time**: Flask-SocketIO for WebSocket communication
- **Authentication**: Flask-Login with bcrypt password hashing
- **Frontend**: Bootstrap 5 with responsive design
- **AI Integration**: Custom chatbot with Excel data support

## Quick Start

### 1. Installation

```bash
# Clone or download the project
cd bank-server

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Data

1. Place your `BankBot_Data_Extended.xlsx` file in the `data/` directory
2. The application will automatically import chatbot data on first run

### 3. Run the Server

```bash
python app.py
```

The server will start on `http://0.0.0.0:5000` (accessible from any device on the same network).

### 4. Access the Application

- **Main Website**: `http://<SERVER_IP>:5000`
- **Customer Dashboard**: `http://<SERVER_IP>:5000/customer/dashboard`
- **Staff Dashboard**: `http://<SERVER_IP>:5000/staff/dashboard`
- **Admin Dashboard**: `http://<SERVER_IP>:5000/admin/dashboard`

## Default Credentials

### Admin
- **Username**: `admin`
- **Password**: `admin123`

### Staff
- **Username**: `staff1`
- **Password**: `staff123`

### Customer
- **Username**: `customer1`
- **Password**: `cust123`

## Network Configuration

### Finding Your Server IP

**Windows:**
```cmd
ipconfig
```
Look for "IPv4 Address" under your WiFi adapter.

**Linux/Mac:**
```bash
ifconfig
```
Look for your WiFi interface IP address.

### Firewall Configuration

**Windows:**
```cmd
netsh advfirewall firewall add rule name="Flask Server" dir=in action=allow protocol=TCP localport=5000
```

**Linux:**
```bash
sudo ufw allow 5000
```

## Project Structure

```
bank-server/
├── app.py                          # Main Flask application
├── config.py                       # Configuration settings
├── requirements.txt                # Python dependencies
├── .gitignore                      # Git ignore rules
│
├── database/
│   ├── __init__.py
│   ├── models.py                   # SQLAlchemy models
│   └── bank_management.db          # SQLite database (auto-generated)
│
├── modules/
│   ├── __init__.py
│   ├── auth.py                     # Authentication logic
│   ├── token_manager.py            # Token generation & management
│   ├── atm_manager.py              # ATM status management
│   ├── user_manager.py             # User CRUD operations
│   ├── analytics.py                # Analytics & reporting
│   └── chatbot_integration.py      # Chatbot wrapper
│
├── api/
│   ├── __init__.py
│   ├── auth_routes.py              # Login, logout, session endpoints
│   ├── customer_routes.py          # Customer-specific endpoints
│   ├── staff_routes.py             # Staff-specific endpoints
│   ├── admin_routes.py             # Admin-specific endpoints
│   └── chatbot_routes.py           # Chatbot API endpoints
│
├── websocket/
│   ├── __init__.py
│   └── events.py                   # SocketIO event handlers
│
├── utils/
│   ├── __init__.py
│   ├── helpers.py                  # Utility functions
│   ├── validators.py               # Input validation
│   └── decorators.py               # Custom decorators
│
├── templates/                      # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── chatbot.html
│   ├── customer_dashboard.html
│   ├── staff_dashboard.html
│   ├── admin_dashboard.html
│   └── error pages (404, 403, 500)
│
├── data/
│   └── BankBot_Data_Extended.xlsx  # Chatbot dataset
│
└── logs/
    └── app.log                     # Application logs
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/session` - Check session status

### Customer
- `GET /api/customer/dashboard` - Customer dashboard data
- `POST /api/customer/token/generate` - Generate new token
- `GET /api/customer/token/history` - Token history
- `DELETE /api/customer/token/:id` - Cancel token

### Staff
- `GET /api/staff/dashboard` - Staff dashboard data
- `GET /api/staff/tokens` - Manage tokens
- `PUT /api/staff/token/:id/status` - Update token status
- `PUT /api/staff/atm/:id` - Update ATM status

### Admin
- `GET /api/admin/dashboard` - Admin dashboard data
- `GET /api/admin/users` - User management
- `POST /api/admin/users` - Create user
- `GET /api/admin/analytics` - Analytics data

### Chatbot
- `POST /api/chatbot/query` - Send message to chatbot
- `GET /api/chatbot/history` - Chat history

## WebSocket Events

### Client → Server
- `connect` - Establish connection
- `join_room` - Join specific room
- `ping` - Heartbeat check

### Server → Client
- `token_generated` - New token created
- `token_updated` - Token status changed
- `token_called` - Token called to counter
- `atm_status_updated` - ATM status changed
- `notification` - General notification

## Database Schema

### Users Table
- `user_id` (Primary Key)
- `username`, `password_hash`, `role`
- `full_name`, `email`, `phone`
- `account_number`, `status`
- `created_at`, `last_login`

### Tokens Table
- `token_id` (Primary Key)
- `token_number`, `customer_id`
- `service_type`, `priority`, `status`
- `counter_number`, `estimated_wait_time`
- `generated_at`, `called_at`, `completed_at`

### ATM Status Table
- `atm_id` (Primary Key)
- `atm_name`, `location`, `status`
- `queue_length`, `cash_available`
- `last_updated`, `updated_by`

## Configuration

Edit `config.py` to customize:

```python
class Config:
    SECRET_KEY = 'your-secret-key'
    HOST = '0.0.0.0'  # Listen on all interfaces
    PORT = 5000
    DEBUG = True
    CORS_ORIGINS = ['*']  # Allow all origins
```

## Troubleshooting

### Cannot Connect from Other Devices
1. Check firewall settings
2. Verify server IP address
3. Ensure all devices are on same WiFi network
4. Test with: `curl http://<SERVER_IP>:5000/api/auth/session`

### Database Errors
1. Delete `database/bank_management.db`
2. Restart the server
3. Check file permissions

### Chatbot Not Working
1. Verify `data/BankBot_Data_Extended.xlsx` exists
2. Check file path in `config.py`
3. Review server logs for import errors

### WebSocket Issues
1. Check CORS settings
2. Ensure `eventlet` is installed
3. Verify browser console for connection errors

## Development

### Adding New Features
1. Create new modules in `modules/` directory
2. Add API routes in `api/` directory
3. Update WebSocket events in `websocket/events.py`
4. Add frontend templates as needed

### Database Migrations
The application automatically creates tables on first run. For schema changes:
1. Update models in `database/models.py`
2. Delete existing database file
3. Restart application

## Security Notes

- Change default admin password in production
- Use environment variables for sensitive data
- Enable HTTPS in production
- Regular security updates recommended

## Support

For issues and questions:
1. Check application logs in `logs/app.log`
2. Verify network connectivity
3. Review configuration settings
4. Test API endpoints with curl/Postman

## License

This project is for educational and demonstration purposes.
