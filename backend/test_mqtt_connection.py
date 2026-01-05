#!/usr/bin/env python3
"""
MQTT Connection Test Script
Tests actual MQTT broker connection using credentials from the API
"""

import sys
import time
import argparse
from typing import Optional

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt not installed")
    print("Install with: pip install paho-mqtt")
    sys.exit(1)


class Colors:
    """ANSI color codes"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class MQTTTester:
    """Test MQTT connection with credentials"""

    def __init__(
        self,
        broker: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool = False,
    ):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

        self.connected = False
        self.message_received = False
        self.test_topic = "smartfactory/test"

        # Create MQTT client
        self.client = mqtt.Client(client_id=f"test_client_{int(time.time())}")
        self.client.username_pw_set(username, password)

        # Set callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_subscribe = self.on_subscribe

    def on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker"""
        if rc == 0:
            self.connected = True
            print(
                f"{Colors.GREEN}✓ Connected to MQTT broker successfully!{Colors.RESET}"
            )
            print(f"{Colors.BLUE}  ℹ Broker: {self.broker}:{self.port}{Colors.RESET}")
            print(f"{Colors.BLUE}  ℹ Username: {self.username}{Colors.RESET}")
        else:
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized",
            }
            error_msg = error_messages.get(rc, f"Unknown error (code {rc})")
            print(f"{Colors.RED}✗ Connection failed: {error_msg}{Colors.RESET}")

    def on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects"""
        if rc != 0:
            print(
                f"{Colors.YELLOW}⚠ Unexpected disconnection (code {rc}){Colors.RESET}"
            )
        else:
            print(f"{Colors.BLUE}ℹ Disconnected from broker{Colors.RESET}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback for when subscription is confirmed"""
        print(f"{Colors.GREEN}✓ Subscribed to topic: {self.test_topic}{Colors.RESET}")
        print(f"{Colors.BLUE}  ℹ QoS level: {granted_qos[0]}{Colors.RESET}")

    def on_publish(self, client, userdata, mid):
        """Callback for when message is published"""
        print(f"{Colors.GREEN}✓ Message published successfully{Colors.RESET}")

    def on_message(self, client, userdata, msg):
        """Callback for when a message is received"""
        self.message_received = True
        print(f"{Colors.GREEN}✓ Message received!{Colors.RESET}")
        print(f"{Colors.BLUE}  ℹ Topic: {msg.topic}{Colors.RESET}")
        print(f"{Colors.BLUE}  ℹ Payload: {msg.payload.decode()}{Colors.RESET}")
        print(f"{Colors.BLUE}  ℹ QoS: {msg.qos}{Colors.RESET}")
        print(f"{Colors.BLUE}  ℹ Retain: {msg.retain}{Colors.RESET}")

    def run_test(self) -> bool:
        """Run the MQTT connection test"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}MQTT Connection Test{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

        try:
            # Connect to broker
            print(
                f"{Colors.YELLOW}Connecting to {self.broker}:{self.port}...{Colors.RESET}"
            )
            self.client.connect(self.broker, self.port, keepalive=60)

            # Start network loop
            self.client.loop_start()

            # Wait for connection
            timeout = 5
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if not self.connected:
                print(
                    f"{Colors.RED}✗ Connection timeout after {timeout}s{Colors.RESET}"
                )
                return False

            # Subscribe to test topic
            print(
                f"\n{Colors.YELLOW}Subscribing to topic: {self.test_topic}{Colors.RESET}"
            )
            self.client.subscribe(self.test_topic, qos=1)
            time.sleep(1)  # Wait for subscription to complete

            # Publish test message
            test_message = f"Test message at {time.strftime('%Y-%m-%d %H:%M:%S')}"
            print(f"\n{Colors.YELLOW}Publishing test message...{Colors.RESET}")
            result = self.client.publish(self.test_topic, test_message, qos=1)

            # Wait for message to be received
            timeout = 5
            start_time = time.time()
            while not self.message_received and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if not self.message_received:
                print(
                    f"{Colors.RED}✗ Message not received after {timeout}s{Colors.RESET}"
                )
                return False

            # Clean up
            time.sleep(1)
            self.client.loop_stop()
            self.client.disconnect()

            # Success summary
            print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
            print(
                f"{Colors.BOLD}{Colors.GREEN}✓ MQTT CONNECTION TEST PASSED!{Colors.RESET}"
            )
            print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

            print(f"{Colors.GREEN}All tests completed successfully:{Colors.RESET}")
            print(f"  ✓ Connected to MQTT broker")
            print(f"  ✓ Authenticated with credentials")
            print(f"  ✓ Subscribed to topic")
            print(f"  ✓ Published message")
            print(f"  ✓ Received message")
            print()

            return True

        except ConnectionRefusedError:
            print(
                f"{Colors.RED}✗ Connection refused - is the MQTT broker running?{Colors.RESET}"
            )
            print(f"{Colors.BLUE}  ℹ Check: docker ps | grep emqx{Colors.RESET}")
            return False

        except Exception as e:
            print(f"{Colors.RED}✗ Error during MQTT test: {str(e)}{Colors.RESET}")
            return False

        finally:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except:
                pass


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Test MQTT connection with credentials from Smart Factory API"
    )
    parser.add_argument(
        "--broker", default="localhost", help="MQTT broker host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=1883, help="MQTT broker port (default: 1883)"
    )
    parser.add_argument(
        "--username",
        required=True,
        help="MQTT username (get from /api/mqtt/credentials)",
    )
    parser.add_argument(
        "--password",
        required=True,
        help="MQTT password (get from /api/mqtt/credentials)",
    )
    parser.add_argument("--tls", action="store_true", help="Use TLS/SSL connection")

    args = parser.parse_args()

    # Run test
    tester = MQTTTester(
        broker=args.broker,
        port=args.port,
        username=args.username,
        password=args.password,
        use_tls=args.tls,
    )

    success = tester.run_test()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
