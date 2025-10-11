#!/usr/bin/env python3
"""
Simple test to verify authentication
"""
import requests
import json

def test_login():
    """Test login functionality"""
    base_url = "http://localhost:5000"
    
    # Test data
    login_data = {
        "username": "customer",
        "password": "customer123"
    }
    
    print("Testing login...")
    
    try:
        response = requests.post(f"{base_url}/api/auth/login", json=login_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_login()
