#!/bin/bash

# Quick MQTT connection test script

echo "🔐 Step 1: Getting JWT Token..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=mqtttest&password=Test123!" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get token. Make sure user 'mqtttest' exists"
    echo "Create user with:"
    echo "curl -X POST http://localhost:8000/api/auth/register -H 'Content-Type: application/json' -d '{\"username\":\"mqtttest\",\"email\":\"mqtttest@example.com\",\"password\":\"Test123!\"}'"
    exit 1
fi

echo "✓ Got JWT token"

echo ""
echo "🔑 Step 2: Getting MQTT credentials..."
CREDS=$(curl -s -X GET http://localhost:8000/api/mqtt/credentials \
  -H "Authorization: Bearer $TOKEN")

echo "$CREDS" | python3 -m json.tool 2>/dev/null || echo "$CREDS"

MQTT_USER=$(echo "$CREDS" | grep -o '"mqtt_username":"[^"]*' | cut -d'"' -f4)
MQTT_PASS=$(echo "$CREDS" | grep -o '"mqtt_password":"[^"]*' | cut -d'"' -f4)

if [ -z "$MQTT_USER" ] || [ -z "$MQTT_PASS" ]; then
    echo "❌ Failed to get MQTT credentials"
    exit 1
fi

echo "✓ Got MQTT credentials"
echo "  Username: $MQTT_USER"
echo "  Password: ${MQTT_PASS:0:10}..."

echo ""
echo "📝 Your MQTT connection details:"
echo "   Broker: localhost"
echo "   Port (TLS): 8883"
echo "   Port (non-TLS): 1883"
echo "   Username: $MQTT_USER"
echo "   Password: $MQTT_PASS"
echo ""
echo "🧪 Step 3: Testing MQTT connection (non-TLS)..."

if command -v python3 &> /dev/null; then
    python3 test_mqtt_connection.py \
        --broker localhost \
        --port 1883 \
        --username "$MQTT_USER" \
        --password "$MQTT_PASS"

else
    echo "❌ Python3 not found. Install mosquitto clients instead:"
    echo "brew install mosquitto"
    echo ""
    echo "Then test with:"
    echo "mosquitto_sub -h localhost -p 1883 -u $MQTT_USER -P $MQTT_PASS -t 'test/topic' -v"
fi

echo ""
echo "Note: Your backend uses TLS on port 8883 inside Docker."
echo "For external TLS testing, you may need SSL certificates."