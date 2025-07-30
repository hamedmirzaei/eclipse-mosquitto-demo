import os
import time

import paho.mqtt.client as mqtt

# Get broker address from environment variable (set in docker-compose)
MQTT_BROKER = os.getenv('MQTT_BROKER_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'docker/test/#')  # Wildcard to catch all messages under 'docker/test/'
CLIENT_ID = "python_subscriber_client"


def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print(f"Subscriber Connected successfully to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}!")
        client.subscribe(MQTT_TOPIC, qos=2)  # Subscribe with QoS 2
        print(f"Subscriber listening on topic: {MQTT_TOPIC}")
    else:
        print(f"Subscriber Failed to connect, return code {rc}")
        # Attempt to reconnect after a delay
        time.sleep(5)
        client.reconnect()


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        print(f"Subscriber received: Topic='{msg.topic}', Message='{payload}' (QoS: {msg.qos}, Retain: {msg.retain})")
    except Exception as e:
        print(f"Error decoding message: {e}")


def on_disconnect(client, userdata, flags, rc, properties):
    print(f"Subscriber disconnected with code {rc}. Attempting to reconnect...")
    # This loop will ensure the subscriber tries to reconnect indefinitely
    while True:
        try:
            client.reconnect()
            break  # If reconnect succeeds, break the loop
        except Exception as e:
            print(f"Reconnect failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)


print(f"Attempting to connect subscriber to {MQTT_BROKER}:{MQTT_PORT} for topic '{MQTT_TOPIC}'...")

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID,
                     protocol=mqtt.MQTTv5)  # Or mqtt.MQTTv5
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)  # Connect with a 60-second keepalive
    client.loop_forever()  # Blocks and handles network traffic indefinitely
except KeyboardInterrupt:
    print("Subscriber stopped manually.")
finally:
    client.disconnect()
    print("Subscriber disconnected.")
