#!/usr/bin/env python3
"""
Servex Holdings Backend API Testing
Tests email/password authentication system
"""

import requests
import sys
from datetime import datetime

class ServexBackendAPITester:
    def __init__(self, base_url="https://warehouse-sync-lab.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.session_token = None

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            self.failed_tests.append({"test": name, "details": details})
            print(f"❌ {name} - FAILED: {details}")

    def make_request(self, method, endpoint, data=None, expected_status=200, headers=None, cookies=None):
        """Make API request"""
        url = f"{self.base_url}/{endpoint}"
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers, cookies=cookies, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers, cookies=cookies, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=default_headers, cookies=cookies, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=default_headers, cookies=cookies, timeout=30)
            
            success = response.status_code == expected_status
            return success, response
        except Exception as e:
            return False, str(e)

    def test_backend_health_endpoint(self):
        """Test backend health check endpoint at /health"""
        print("\n🏥 Testing Backend Health Endpoint...")
        
        success, response = self.make_request('GET', 'health', expected_status=200)
        if success:
            try:
                data = response.json()
                success = (data.get('status') == 'healthy' and 
                          'version' in data)
            except:
                success = False
        
        self.log_test("Backend health check endpoint (/health)", success, 
                     response.text if hasattr(response, 'text') else str(response))

    def test_backend_root_endpoint(self):
        """Test backend root endpoint at /"""
        print("\n🏠 Testing Backend Root Endpoint...")
        
        success, response = self.make_request('GET', '', expected_status=200)
        if success:
            try:
                data = response.json()
                success = ('message' in data and 
                          'version' in data and
                          'Servex Holdings' in data.get('message', ''))
            except:
                success = False
        
        self.log_test("Backend root endpoint (/)", success,
                     response.text if hasattr(response, 'text') else str(response))

    def test_auth_me_unauthenticated(self):
        """Test /api/auth/me returns 401 when not authenticated"""
        print("\n🔒 Testing Auth Endpoint Unauthenticated Access...")
        
        success, response = self.make_request('GET', 'api/auth/me', expected_status=401)
        if success:
            try:
                data = response.json()
                success = 'detail' in data
            except:
                success = False
        
        self.log_test("Auth endpoint /api/auth/me returns 401 when unauthenticated", success,
                     response.text if hasattr(response, 'text') else str(response))

    def test_clients_api_unauthenticated(self):
        """Test /api/clients returns 401 when unauthenticated"""
        print("\n👥 Testing Clients API Unauthenticated Access...")
        
        success, response = self.make_request('GET', 'api/clients', expected_status=401)
        if success:
            try:
                data = response.json()
                success = 'detail' in data
            except:
                success = False
        
        self.log_test("API /api/clients returns 401 when unauthenticated", success,
                     response.text if hasattr(response, 'text') else str(response))

    def test_shipments_api_unauthenticated(self):
        """Test /api/shipments returns 401 when unauthenticated"""
        print("\n📦 Testing Shipments API Unauthenticated Access...")
        
        success, response = self.make_request('GET', 'api/shipments', expected_status=401)
        if success:
            try:
                data = response.json()
                success = 'detail' in data
            except:
                success = False
        
        self.log_test("API /api/shipments returns 401 when unauthenticated", success,
                     response.text if hasattr(response, 'text') else str(response))

    def test_admin_login(self):
        """Test admin login with admin@servex.com and Servex2026!"""
        print("\n🔐 Testing Admin Login...")
        
        success, response = self.make_request('POST', 'api/auth/login', 
                                            data={
                                                'email': 'admin@servex.com',
                                                'password': 'Servex2026!'
                                            },
                                            expected_status=200)
        if success:
            try:
                data = response.json()
                # Check if we got user data back
                success = (data.get('email') == 'admin@servex.com' and
                          data.get('name') == 'Admin User' and
                          'id' in data and
                          'tenant_id' in data)
                
                # Store cookies for authenticated requests
                if success and response.cookies:
                    self.session_token = response.cookies.get('session_token')
                    
            except:
                success = False
        
        self.log_test("Admin login with correct credentials", success,
                     response.text if hasattr(response, 'text') else str(response))
        return success

    def test_invalid_login(self):
        """Test login with invalid credentials"""
        print("\n❌ Testing Invalid Login...")
        
        success, response = self.make_request('POST', 'api/auth/login',
                                            data={
                                                'email': 'admin@servex.com',
                                                'password': 'wrongpassword'
                                            },
                                            expected_status=401)
        if success:
            try:
                data = response.json()
                success = 'detail' in data and 'Invalid email or password' in data['detail']
            except:
                success = False
        
        self.log_test("Invalid login returns 401 with error message", success,
                     response.text if hasattr(response, 'text') else str(response))

    def test_auth_me_authenticated(self):
        """Test /api/auth/me when authenticated"""
        print("\n👤 Testing Authenticated User Info...")
        
        if not self.session_token:
            self.log_test("Get authenticated user info", False, "No session token available")
            return
        
        cookies = {'session_token': self.session_token}
        success, response = self.make_request('GET', 'api/auth/me', 
                                            cookies=cookies, expected_status=200)
        if success:
            try:
                data = response.json()
                success = (data.get('email') == 'admin@servex.com' and
                          data.get('name') == 'Admin User' and
                          'id' in data)
            except:
                success = False
        
        self.log_test("Get authenticated user info", success,
                     response.text if hasattr(response, 'text') else str(response))

    def test_logout(self):
        """Test logout functionality"""
        print("\n🚪 Testing Logout...")
        
        if not self.session_token:
            self.log_test("Logout functionality", False, "No session token available")
            return
        
        cookies = {'session_token': self.session_token}
        success, response = self.make_request('POST', 'api/auth/logout',
                                            cookies=cookies, expected_status=200)
        if success:
            try:
                data = response.json()
                success = 'message' in data and 'Logged out successfully' in data['message']
            except:
                success = False
        
        self.log_test("Logout functionality", success,
                     response.text if hasattr(response, 'text') else str(response))
        
        # Clear session token
        self.session_token = None

    def run_all_tests(self):
        """Run complete test suite for Servex Holdings backend verification"""
        print("🚀 Starting Servex Holdings Email/Password Authentication Tests")
        print("=" * 65)
        
        # Backend health checks
        self.test_backend_health_endpoint()
        self.test_backend_root_endpoint()
        
        # Authentication flow tests
        self.test_admin_login()
        self.test_invalid_login()
        self.test_auth_me_authenticated()
        self.test_logout()
        
        # Unauthenticated access tests
        self.test_auth_me_unauthenticated()
        self.test_clients_api_unauthenticated()  
        self.test_shipments_api_unauthenticated()
        
        # Results
        print("\n" + "=" * 65)
        print(f"📊 TEST RESULTS: {self.tests_passed}/{self.tests_run} PASSED")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for failure in self.failed_tests:
                print(f"  • {failure['test']}: {failure['details']}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"✅ Success Rate: {success_rate:.1f}%")
        return success_rate >= 80

def main():
    """Main test runner"""
    tester = ServexBackendAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())