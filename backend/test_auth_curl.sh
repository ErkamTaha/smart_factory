#!/bin/bash

# Authentication Backend Test Suite using curl
# Tests the complete authentication flow

# Configuration
BASE_URL="http://localhost:8000"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_USERNAME="test_user_${TIMESTAMP}"
TEST_EMAIL="test_${TIMESTAMP}@example.com"
TEST_PASSWORD="SecureTestPassword123!"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Functions
print_header() {
    echo -e "\n${BOLD}${BLUE}============================================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}============================================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}Testing:${NC} $1"
}

print_success() {
    echo -e "  ${GREEN}✓ $1${NC}"
    ((PASSED_TESTS++))
    ((TOTAL_TESTS++))
}

print_error() {
    echo -e "  ${RED}✗ $1${NC}"
    ((FAILED_TESTS++))
    ((TOTAL_TESTS++))
}

print_info() {
    echo -e "  ${BLUE}ℹ $1${NC}"
}

# Test 1: Server Health
test_server_health() {
    print_test "Server Health Check"

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" ${BASE_URL}/)

    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Server is running at ${BASE_URL}"
        return 0
    else
        print_error "Server is not accessible (HTTP ${HTTP_CODE})"
        print_info "Start the server with: cd backend && uvicorn app.main:app --reload"
        return 1
    fi
}

# Test 2: Unauthorized Access Protection
test_unauthorized_access() {
    print_test "Unauthorized Access Protection"

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" ${BASE_URL}/api/mqtt/credentials)

    if [ "$HTTP_CODE" = "401" ]; then
        print_success "Endpoint correctly rejects unauthorized access"
        print_info "Status code: 401 Unauthorized"
    else
        print_error "Endpoint allowed unauthorized access! Status: ${HTTP_CODE}"
    fi
}

# Test 3: User Registration
test_registration() {
    print_test "User Registration"

    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST ${BASE_URL}/api/auth/register \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"${TEST_USERNAME}\",
            \"email\": \"${TEST_EMAIL}\",
            \"password\": \"${TEST_PASSWORD}\"
        }")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "201" ]; then
        print_success "User registered successfully"
        USER_ID=$(echo "$BODY" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
        USERNAME=$(echo "$BODY" | grep -o '"username":"[^"]*' | cut -d'"' -f4)
        print_info "Username: ${USERNAME}"
        print_info "User ID: ${USER_ID}"
    else
        print_error "Registration failed (HTTP ${HTTP_CODE})"
        print_info "Response: ${BODY}"
    fi
}

# Test 4: User Login
test_login() {
    print_test "User Login & JWT Token Generation"

    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST ${BASE_URL}/api/auth/login \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=${TEST_USERNAME}&password=${TEST_PASSWORD}")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Login successful"
        ACCESS_TOKEN=$(echo "$BODY" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        TOKEN_TYPE=$(echo "$BODY" | grep -o '"token_type":"[^"]*' | cut -d'"' -f4)
        print_info "Token type: ${TOKEN_TYPE}"
        print_info "Access token (first 20 chars): ${ACCESS_TOKEN:0:20}..."

        # Export token for use in other tests
        export JWT_TOKEN="$ACCESS_TOKEN"
    else
        print_error "Login failed (HTTP ${HTTP_CODE})"
        print_info "Response: ${BODY}"
        export JWT_TOKEN=""
    fi
}

# Test 5: Get Current User
test_get_current_user() {
    if [ -z "$JWT_TOKEN" ]; then
        print_error "No JWT token available, skipping test"
        return
    fi

    print_test "Get Current User Info"

    RESPONSE=$(curl -s -w "\n%{http_code}" -X GET ${BASE_URL}/api/auth/me \
        -H "Authorization: Bearer ${JWT_TOKEN}")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Retrieved current user info"
        USERNAME=$(echo "$BODY" | grep -o '"username":"[^"]*' | cut -d'"' -f4)
        EMAIL=$(echo "$BODY" | grep -o '"email":"[^"]*' | cut -d'"' -f4)
        print_info "Username: ${USERNAME}"
        print_info "Email: ${EMAIL}"
    else
        print_error "Failed to get user info (HTTP ${HTTP_CODE})"
        print_info "Response: ${BODY}"
    fi
}

# Test 6: MQTT Credentials Retrieval
test_mqtt_credentials() {
    if [ -z "$JWT_TOKEN" ]; then
        print_error "No JWT token available, skipping test"
        return
    fi

    print_test "MQTT Credentials Retrieval"

    RESPONSE=$(curl -s -w "\n%{http_code}" -X GET ${BASE_URL}/api/mqtt/credentials \
        -H "Authorization: Bearer ${JWT_TOKEN}")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        print_success "MQTT credentials retrieved successfully"
        MQTT_USERNAME=$(echo "$BODY" | grep -o '"mqtt_username":"[^"]*' | cut -d'"' -f4)
        MQTT_PASSWORD=$(echo "$BODY" | grep -o '"mqtt_password":"[^"]*' | cut -d'"' -f4)
        MQTT_BROKER=$(echo "$BODY" | grep -o '"mqtt_broker":"[^"]*' | cut -d'"' -f4)
        MQTT_PORT=$(echo "$BODY" | grep -o '"mqtt_port":[0-9]*' | cut -d':' -f2)

        print_info "MQTT Username: ${MQTT_USERNAME}"
        print_info "MQTT Password (first 10 chars): ${MQTT_PASSWORD:0:10}..."
        print_info "MQTT Broker: ${MQTT_BROKER}"
        print_info "MQTT Port: ${MQTT_PORT}"

        # Save for persistence test
        export FIRST_MQTT_USERNAME="$MQTT_USERNAME"
        export FIRST_MQTT_PASSWORD="$MQTT_PASSWORD"
    else
        print_error "Failed to get MQTT credentials (HTTP ${HTTP_CODE})"
        print_info "Response: ${BODY}"
    fi
}

# Test 7: MQTT Credentials Persistence
test_mqtt_persistence() {
    if [ -z "$JWT_TOKEN" ] || [ -z "$FIRST_MQTT_PASSWORD" ]; then
        print_error "Prerequisites not met, skipping test"
        return
    fi

    print_test "MQTT Credentials Persistence"

    RESPONSE=$(curl -s -w "\n%{http_code}" -X GET ${BASE_URL}/api/mqtt/credentials \
        -H "Authorization: Bearer ${JWT_TOKEN}")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        SECOND_MQTT_USERNAME=$(echo "$BODY" | grep -o '"mqtt_username":"[^"]*' | cut -d'"' -f4)
        SECOND_MQTT_PASSWORD=$(echo "$BODY" | grep -o '"mqtt_password":"[^"]*' | cut -d'"' -f4)

        if [ "$FIRST_MQTT_USERNAME" = "$SECOND_MQTT_USERNAME" ] && [ "$FIRST_MQTT_PASSWORD" = "$SECOND_MQTT_PASSWORD" ]; then
            print_success "MQTT credentials are persistent (not regenerated)"
            print_info "Username matches: ✓"
            print_info "Password matches: ✓"
        else
            print_error "MQTT credentials were regenerated (should be persistent!)"
        fi
    else
        print_error "Failed to retrieve credentials again (HTTP ${HTTP_CODE})"
    fi
}

# Test 8: Invalid Token
test_invalid_token() {
    print_test "Invalid Token Protection"

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET ${BASE_URL}/api/mqtt/credentials \
        -H "Authorization: Bearer invalid_token_12345")

    if [ "$HTTP_CODE" = "401" ]; then
        print_success "Invalid token correctly rejected"
        print_info "Status code: 401 Unauthorized"
    else
        print_error "Invalid token was accepted! Status: ${HTTP_CODE}"
    fi
}

# Test 9: Token Refresh
test_token_refresh() {
    if [ -z "$JWT_TOKEN" ]; then
        print_error "No JWT token available, skipping test"
        return
    fi

    print_test "Token Refresh"

    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST ${BASE_URL}/api/auth/refresh \
        -H "Authorization: Bearer ${JWT_TOKEN}")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        NEW_TOKEN=$(echo "$BODY" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        print_success "Token refreshed successfully"
        print_info "New token (first 20 chars): ${NEW_TOKEN:0:20}..."
        if [ "$NEW_TOKEN" != "$JWT_TOKEN" ]; then
            print_info "Tokens are different: ✓"
        fi
    else
        print_error "Token refresh failed (HTTP ${HTTP_CODE})"
    fi
}

# Print summary
print_summary() {
    print_header "TEST SUMMARY"

    PASS_RATE=0
    if [ $TOTAL_TESTS -gt 0 ]; then
        PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    fi

    echo "Total Tests: ${TOTAL_TESTS}"
    echo -e "${GREEN}Passed: ${PASSED_TESTS}${NC}"
    echo -e "${RED}Failed: ${FAILED_TESTS}${NC}"
    echo "Pass Rate: ${PASS_RATE}%"
    echo

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}${BOLD}✓ ALL TESTS PASSED!${NC}\n"
        exit 0
    else
        echo -e "${RED}${BOLD}✗ SOME TESTS FAILED${NC}\n"
        exit 1
    fi
}

# Main execution
main() {
    print_header "SMART FACTORY - AUTHENTICATION BACKEND TEST SUITE"
    echo "Test User: ${TEST_USERNAME}"
    echo "Base URL: ${BASE_URL}"
    echo "Started at: $(date '+%Y-%m-%d %H:%M:%S')"
    echo

    # Run tests in sequence
    if ! test_server_health; then
        print_error "Server is not accessible. Aborting tests."
        print_info "Start the server with: cd backend && uvicorn app.main:app --reload"
        exit 1
    fi

    test_unauthorized_access
    test_invalid_token
    test_registration
    test_login
    test_get_current_user
    test_mqtt_credentials
    test_mqtt_persistence
    test_token_refresh

    print_summary
}

# Run main function
main