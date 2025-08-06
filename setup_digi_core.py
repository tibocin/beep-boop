#!/usr/bin/env python3
"""
setup_digi_core.py - Digi-Core Setup and Data Processing Script

This script helps set up Digi-Core integration by:
1. Creating an API key for Beep-Boop
2. Processing personal data into the knowledge base
3. Testing the integration

File: setup_digi_core.py
Purpose: Setup and configure digi-core integration
Related: DigiCoreBackend, data processing
Tags: setup, digi-core, configuration, data-processing
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_api_key():
    """Create a new API key for Beep-Boop integration."""
    print("🔑 Creating Digi-Core API key for Beep-Boop...")
    
    api_url = os.getenv('DIGI_CORE_API_URL', 'http://localhost:8000')
    
    try:
        response = requests.post(
            f"{api_url}/apps/",
            headers={"Content-Type": "application/json"},
            json={
                "name": "beep-boop-integration",
                "scopes": "read,write,admin"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            api_key_data = response.json()
            api_key = api_key_data.get('api_key')
            
            if api_key:
                print("✅ API key created successfully!")
                print(f"API Key: {api_key}")
                print("\n📝 Add this to your .env file:")
                print(f"DIGI_CORE_API_KEY={api_key}")
                return api_key
            else:
                print("❌ No API key in response")
                return None
        else:
            print(f"❌ Failed to create API key: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating API key: {str(e)}")
        return None

def process_data(api_key: str):
    """Process personal data into Digi-Core knowledge base."""
    print("\n📚 Processing personal data into Digi-Core...")
    
    api_url = os.getenv('DIGI_CORE_API_URL', 'http://localhost:8000')
    
    try:
        response = requests.post(
            f"{api_url}/apps/process-data?incremental=true",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Data processing completed successfully!")
            return True
        else:
            print(f"❌ Data processing failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing data: {str(e)}")
        return False

def test_integration(api_key: str):
    """Test the integration with sample queries."""
    print("\n🧪 Testing integration with sample queries...")
    
    api_url = os.getenv('DIGI_CORE_API_URL', 'http://localhost:8000')
    
    test_queries = [
        "What are my technical skills?",
        "What projects am I working on?",
        "What are my interests?"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        
        try:
            response = requests.post(
                f"{api_url}/query/",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                confidence = result.get('confidence', 0)
                answer = result.get('answer', 'No answer')
                
                print(f"✅ Confidence: {confidence:.2f}")
                print(f"Answer: {answer[:100]}{'...' if len(answer) > 100 else ''}")
            else:
                print(f"❌ Query failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")

def check_health():
    """Check Digi-Core health."""
    print("🏥 Checking Digi-Core health...")
    
    api_url = os.getenv('DIGI_CORE_API_URL', 'http://localhost:8000')
    
    try:
        response = requests.get(f"{api_url}/healthz", timeout=5)
        
        if response.status_code == 200:
            print("✅ Digi-Core is healthy and ready")
            return True
        else:
            print(f"❌ Digi-Core health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Cannot connect to Digi-Core: {str(e)}")
        return False

def main():
    """Main setup function."""
    print("🚀 Digi-Core Setup for Beep-Boop")
    print("=" * 40)
    
    # Check if Digi-Core is running
    if not check_health():
        print("\n❌ Digi-Core is not available.")
        print("Please ensure Digi-Core is running on http://localhost:8000")
        return False
    
    # Check if API key already exists
    existing_api_key = os.getenv('DIGI_CORE_API_KEY')
    if existing_api_key:
        print(f"🔑 Using existing API key: {existing_api_key[:10]}...")
        api_key = existing_api_key
    else:
        # Create new API key
        api_key = create_api_key()
        if not api_key:
            return False
    
    # Process data
    if not process_data(api_key):
        return False
    
    # Test integration
    test_integration(api_key)
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Add the API key to your .env file if not already done")
    print("2. Run the test script: python test_digi_core_integration.py")
    print("3. Start Beep-Boop: python app.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 