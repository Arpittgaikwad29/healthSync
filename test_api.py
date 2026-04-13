"""
Test script for MediGraph Healthcare Backend
Run this to verify all endpoints are working
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def print_response(response, title):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")
    print(f"{'='*60}\n")

def test_health_check():
    """Test health check endpoints"""
    print("\n🏥 Testing Health Checks...")
    
    # Root endpoint
    response = requests.get(f"{BASE_URL}/")
    print_response(response, "Root Endpoint")
    
    # Health endpoint
    response = requests.get(f"{BASE_URL}/health")
    print_response(response, "Health Check")

def test_registration():
    """Test user registration"""
    print("\n👤 Testing User Registration...")
    
    # Register patient
    data = {
        "user_id": "TEST_PATIENT_001",
        "password": "testpass123",
        "user_type": "Patient"
    }
    response = requests.post(f"{BASE_URL}/api/auth/register", json=data)
    print_response(response, "Register Patient")
    
    # Register doctor
    data = {
        "user_id": "TEST_DOCTOR_001",
        "password": "docpass123",
        "user_type": "Doctor"
    }
    response = requests.post(f"{BASE_URL}/api/auth/register", json=data)
    print_response(response, "Register Doctor")

def test_login():
    """Test user login"""
    print("\n🔐 Testing User Login...")
    
    # Login patient
    data = {
        "user_id": "TEST_PATIENT_001",
        "password": "testpass123"
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", json=data)
    print_response(response, "Login Patient")
    
    # Login with wrong password
    data = {
        "user_id": "TEST_PATIENT_001",
        "password": "wrongpassword"
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", json=data)
    print_response(response, "Login with Wrong Password (Should Fail)")

def test_patient_summary():
    """Test patient summary endpoint"""
    print("\n📊 Testing Patient Summary...")
    
    # This will fail if patient doesn't exist yet
    response = requests.get(f"{BASE_URL}/api/patient/TEST_PATIENT_001/summary")
    print_response(response, "Get Patient Summary")

def test_upload_prescription():
    """Test prescription upload (requires actual image file)"""
    print("\n📤 Testing Prescription Upload...")
    print("⚠️  Note: This requires an actual image file")
    print("    Create a test image and uncomment the code below\n")
    
    # Uncomment this when you have a test image:
    """
    files = {'file': open('test_prescription.jpg', 'rb')}
    data = {'patient_id': 'TEST_PATIENT_001'}
    response = requests.post(
        f"{BASE_URL}/api/process-prescription",
        files=files,
        data=data,
        stream=True
    )
    
    print("Streaming Response:")
    for line in response.iter_lines():
        if line:
            print(line.decode('utf-8'))
    """

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 MEDIAGRAPH BACKEND API TESTS")
    print("="*60)
    
    try:
        test_health_check()
        test_registration()
        test_login()
        test_patient_summary()
        test_upload_prescription()
        
        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60)
        print("\n💡 Tips:")
        print("   - If registration fails, users might already exist")
        print("   - Patient summary will be empty until you upload a prescription")
        print("   - Upload a prescription from the frontend to test the full flow")
        print("\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend!")
        print("   Make sure the backend is running on http://localhost:8000")
        print("   Run: python main.py\n")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")

if __name__ == "__main__":
    run_all_tests()
