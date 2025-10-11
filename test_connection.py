#!/usr/bin/env python3
"""
Test script to verify frontend-backend connectivity
"""
import requests
import json
import time

def test_api_connection():
    """Test API endpoints connectivity"""
    base_url = "http://localhost:5000"
    
    print("Testing API Connectivity...")
    
    # Test 1: Home page
    try:
        response = requests.get(f"{base_url}/")
        print(f"Home page: {response.status_code}")
    except Exception as e:
        print(f"Home page error: {e}")
    
    # Test 2: Login page
    try:
        response = requests.get(f"{base_url}/login")
        print(f"Login page: {response.status_code}")
    except Exception as e:
        print(f"Login page error: {e}")
    
    # Test 3: API endpoints (should redirect to login)
    try:
        response = requests.get(f"{base_url}/api/customer/dashboard")
        print(f"Customer API (redirect): {response.status_code}")
    except Exception as e:
        print(f"Customer API error: {e}")
    
    # Test 4: WebSocket endpoint
    try:
        response = requests.get(f"{base_url}/socket.io/")
        print(f"WebSocket endpoint: {response.status_code}")
    except Exception as e:
        print(f"WebSocket endpoint error: {e}")

def test_authentication():
    """Test authentication flow"""
    base_url = "http://localhost:5000"
    
    print("\nTesting Authentication...")
    
    # Create session
    session = requests.Session()
    
    # Test login
    login_data = {
        "username": "customer",
        "password": "customer123"
    }
    
    try:
        response = session.post(f"{base_url}/api/auth/login", json=login_data)
        print(f"Login response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Message: {data.get('message', 'No message')}")
    except Exception as e:
        print(f"Login failed: {e}")
        return False
    
    # Test authenticated API call
    try:
        response = session.get(f"{base_url}/api/customer/dashboard")
        print(f"Authenticated API: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Profile: {data.get('profile', {}).get('username', 'No username')}")
    except Exception as e:
        print(f"Authenticated API failed: {e}")
        return False
    
    return True

def test_websocket_connection():
    """Test WebSocket connectivity"""
    print("\nTesting WebSocket Connection...")
    
    try:
        import socketio
        
        # Create SocketIO client
        sio = socketio.Client()
        
        @sio.event
        def connect():
            print("WebSocket connected successfully")
            sio.disconnect()
        
        @sio.event
        def disconnect():
            print("WebSocket disconnected")
        
        # Connect to server
        sio.connect('http://localhost:5000')
        time.sleep(1)
        
    except ImportError:
        print("SocketIO client not available. Install: pip install python-socketio")
    except Exception as e:
        print(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    print("Bank Management System - Connection Test")
    print("=" * 50)
    
    test_api_connection()
    test_authentication()
    test_websocket_connection()
    
    print("\n" + "=" * 50)
    print("Connection test completed!")
