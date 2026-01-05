#!/usr/bin/env python3
"""
Authentication Backend Test Suite
Tests the complete authentication flow including:
- User registration
- User login
- JWT token handling
- MQTT credentials retrieval
- EMQX integration
"""

import httpx
import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER = {
    "username": f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    "email": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
    "password": "SecureTestPassword123!",
}

# Test results tracking
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "errors": [],
}


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def print_test(test_name: str):
    """Print test name"""
    print(f"{Colors.YELLOW}Testing:{Colors.RESET} {test_name}")


def print_success(message: str):
    """Print success message"""
    print(f"  {Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message"""
    print(f"  {Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message: str):
    """Print info message"""
    print(f"  {Colors.BLUE}ℹ {message}{Colors.RESET}")


def record_result(passed: bool, error_msg: Optional[str] = None):
    """Record test result"""
    test_results["total"] += 1
    if passed:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
        if error_msg:
            test_results["errors"].append(error_msg)


async def test_server_health() -> bool:
    """Test if the server is running"""
    print_test("Server Health Check")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BASE_URL}/")
            if response.status_code == 200:
                print_success(f"Server is running at {BASE_URL}")
                record_result(True)
                return True
            else:
                print_error(f"Server returned status code: {response.status_code}")
                record_result(
                    False, f"Server health check failed: {response.status_code}"
                )
                return False
    except httpx.ConnectError:
        print_error(f"Cannot connect to server at {BASE_URL}")
        print_info(
            "Make sure the server is running with: uvicorn app.main:app --reload"
        )
        record_result(False, "Cannot connect to server")
        return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        record_result(False, f"Server health check error: {str(e)}")
        return False


async def test_user_registration() -> Dict[str, Any]:
    """Test user registration endpoint"""
    print_test("User Registration")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{BASE_URL}/api/auth/register", json=TEST_USER
            )

            if response.status_code == 201:
                user_data = response.json()
                print_success("User registered successfully")
                print_info(f"Username: {user_data.get('username')}")
                print_info(f"Email: {user_data.get('email')}")
                print_info(f"User ID: {user_data.get('id')}")
                record_result(True)
                return user_data
            else:
                error_detail = response.json().get("detail", "Unknown error")
                print_error(f"Registration failed: {error_detail}")
                print_info(f"Status code: {response.status_code}")
                print_info(f"Response: {response.text}")
                record_result(False, f"Registration failed: {error_detail}")
                return None
    except Exception as e:
        print_error(f"Error during registration: {str(e)}")
        record_result(False, f"Registration error: {str(e)}")
        return None


async def test_user_login() -> Optional[str]:
    """Test user login and JWT token generation"""
    print_test("User Login & JWT Token Generation")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Login uses form data, not JSON
            response = await client.post(
                f"{BASE_URL}/api/auth/login",
                data={
                    "username": TEST_USER["username"],
                    "password": TEST_USER["password"],
                },
            )

            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")
                token_type = token_data.get("token_type")

                print_success("Login successful")
                print_info(f"Token type: {token_type}")
                print_info(f"Access token (first 20 chars): {access_token[:20]}...")
                record_result(True)
                return access_token
            else:
                error_detail = response.json().get("detail", "Unknown error")
                print_error(f"Login failed: {error_detail}")
                print_info(f"Status code: {response.status_code}")
                record_result(False, f"Login failed: {error_detail}")
                return None
    except Exception as e:
        print_error(f"Error during login: {str(e)}")
        record_result(False, f"Login error: {str(e)}")
        return None


async def test_get_current_user(token: str) -> bool:
    """Test getting current user info with JWT token"""
    print_test("Get Current User Info")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                user_data = response.json()
                print_success("Retrieved current user info")
                print_info(f"Username: {user_data.get('username')}")
                print_info(f"Email: {user_data.get('email')}")
                print_info(f"Active: {user_data.get('is_active')}")
                record_result(True)
                return True
            else:
                error_detail = response.json().get("detail", "Unknown error")
                print_error(f"Failed to get user info: {error_detail}")
                record_result(False, f"Get user info failed: {error_detail}")
                return False
    except Exception as e:
        print_error(f"Error getting user info: {str(e)}")
        record_result(False, f"Get user info error: {str(e)}")
        return False


async def test_mqtt_credentials(token: str) -> Optional[Dict[str, Any]]:
    """Test MQTT credentials retrieval with JWT token"""
    print_test("MQTT Credentials Retrieval")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/api/mqtt/credentials",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code == 200:
                mqtt_data = response.json()
                print_success("MQTT credentials retrieved successfully")
                print_info(f"MQTT Username: {mqtt_data.get('mqtt_username')}")
                print_info(
                    f"MQTT Password (first 10 chars): {mqtt_data.get('mqtt_password', '')[:10]}..."
                )
                print_info(f"MQTT Broker: {mqtt_data.get('mqtt_broker')}")
                print_info(f"MQTT Port: {mqtt_data.get('mqtt_port')}")
                print_info(f"TLS Enabled: {mqtt_data.get('mqtt_tls_enabled')}")
                print_info(f"WebSocket Port: {mqtt_data.get('mqtt_ws_port')}")
                record_result(True)
                return mqtt_data
            else:
                error_detail = response.json().get("detail", "Unknown error")
                print_error(f"Failed to get MQTT credentials: {error_detail}")
                print_info(f"Status code: {response.status_code}")
                record_result(False, f"MQTT credentials failed: {error_detail}")
                return None
    except Exception as e:
        print_error(f"Error getting MQTT credentials: {str(e)}")
        record_result(False, f"MQTT credentials error: {str(e)}")
        return None


async def test_mqtt_credentials_persistence(
    token: str, first_credentials: Dict[str, Any]
) -> bool:
    """Test that MQTT credentials persist (not regenerated on every call)"""
    print_test("MQTT Credentials Persistence")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/api/mqtt/credentials",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code == 200:
                second_credentials = response.json()

                if first_credentials.get("mqtt_username") == second_credentials.get(
                    "mqtt_username"
                ) and first_credentials.get("mqtt_password") == second_credentials.get(
                    "mqtt_password"
                ):
                    print_success("MQTT credentials are persistent (not regenerated)")
                    print_info("Username matches: ✓")
                    print_info("Password matches: ✓")
                    record_result(True)
                    return True
                else:
                    print_error(
                        "MQTT credentials were regenerated (should be persistent!)"
                    )
                    record_result(False, "MQTT credentials not persistent")
                    return False
            else:
                print_error(
                    f"Failed to retrieve credentials again: {response.status_code}"
                )
                record_result(False, "Failed to test persistence")
                return False
    except Exception as e:
        print_error(f"Error testing persistence: {str(e)}")
        record_result(False, f"Persistence test error: {str(e)}")
        return False


async def test_unauthorized_access() -> bool:
    """Test that endpoints require authentication"""
    print_test("Unauthorized Access Protection")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to access MQTT credentials without token
            response = await client.get(f"{BASE_URL}/api/mqtt/credentials")

            if response.status_code == 401:
                print_success("Endpoint correctly rejects unauthorized access")
                print_info("Status code: 401 Unauthorized")
                record_result(True)
                return True
            else:
                print_error(
                    f"Endpoint allowed unauthorized access! Status: {response.status_code}"
                )
                record_result(False, "Unauthorized access not blocked")
                return False
    except Exception as e:
        print_error(f"Error testing unauthorized access: {str(e)}")
        record_result(False, f"Unauthorized test error: {str(e)}")
        return False


async def test_invalid_token() -> bool:
    """Test that invalid tokens are rejected"""
    print_test("Invalid Token Protection")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try with invalid token
            response = await client.get(
                f"{BASE_URL}/api/mqtt/credentials",
                headers={"Authorization": "Bearer invalid_token_12345"},
            )

            if response.status_code == 401:
                print_success("Invalid token correctly rejected")
                print_info("Status code: 401 Unauthorized")
                record_result(True)
                return True
            else:
                print_error(
                    f"Invalid token was accepted! Status: {response.status_code}"
                )
                record_result(False, "Invalid token not rejected")
                return False
    except Exception as e:
        print_error(f"Error testing invalid token: {str(e)}")
        record_result(False, f"Invalid token test error: {str(e)}")
        return False


async def test_token_refresh(token: str) -> bool:
    """Test token refresh endpoint"""
    print_test("Token Refresh")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{BASE_URL}/api/auth/refresh",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code == 200:
                token_data = response.json()
                new_token = token_data.get("access_token")
                print_success("Token refreshed successfully")
                print_info(f"New token (first 20 chars): {new_token[:20]}...")
                print_info(f"Tokens are different: {new_token != token}")
                record_result(True)
                return True
            else:
                print_error(f"Token refresh failed: {response.status_code}")
                record_result(False, f"Token refresh failed: {response.status_code}")
                return False
    except Exception as e:
        print_error(f"Error refreshing token: {str(e)}")
        record_result(False, f"Token refresh error: {str(e)}")
        return False


def print_summary():
    """Print test summary"""
    print_header("TEST SUMMARY")

    total = test_results["total"]
    passed = test_results["passed"]
    failed = test_results["failed"]
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"Total Tests: {total}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
    print(f"Pass Rate: {pass_rate:.1f}%\n")

    if test_results["errors"]:
        print(f"{Colors.RED}Errors encountered:{Colors.RESET}")
        for i, error in enumerate(test_results["errors"], 1):
            print(f"  {i}. {error}")
        print()

    if failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED!{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.RESET}\n")
        return 1


async def run_all_tests():
    """Run all authentication tests"""
    print_header("SMART FACTORY - AUTHENTICATION BACKEND TEST SUITE")
    print(f"Test User: {TEST_USER['username']}")
    print(f"Base URL: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Test 1: Server health
    server_ok = await test_server_health()
    if not server_ok:
        print_error("\nServer is not accessible. Aborting tests.")
        return print_summary()

    # Test 2: Unauthorized access protection
    await test_unauthorized_access()

    # Test 3: Invalid token protection
    await test_invalid_token()

    # Test 4: User registration
    user_data = await test_user_registration()
    if not user_data:
        print_error("\nUser registration failed. Aborting remaining tests.")
        return print_summary()

    # Test 5: User login
    token = await test_user_login()
    if not token:
        print_error("\nLogin failed. Aborting remaining tests.")
        return print_summary()

    # Test 6: Get current user
    await test_get_current_user(token)

    # Test 7: MQTT credentials retrieval
    mqtt_creds = await test_mqtt_credentials(token)
    if not mqtt_creds:
        print_error("\nMQTT credentials retrieval failed.")

    # Test 8: MQTT credentials persistence
    if mqtt_creds:
        await test_mqtt_credentials_persistence(token, mqtt_creds)

    # Test 9: Token refresh
    await test_token_refresh(token)

    # Print summary
    return print_summary()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run_all_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {str(e)}{Colors.RESET}")
        sys.exit(1)
