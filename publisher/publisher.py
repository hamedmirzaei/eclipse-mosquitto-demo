import os
import time

import paho.mqtt.client as mqtt

# Get broker address from environment variable (set in docker-compose)
MQTT_BROKER = os.getenv('MQTT_BROKER_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'docker/test/message')
CLIENT_ID = "python_publisher_client"


def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print(f"Publisher Connected successfully to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}!")
    else:
        print(f"Publisher Failed to connect, return code {rc}")


def on_disconnect(client, userdata, flags, rc, properties):
    if rc != 0:
        print(f"Publisher {client._client_id} unexpectedly disconnected (RC: {rc}).")


print(f"Attempting to connect publisher to {MQTT_BROKER}:{MQTT_PORT} for topic '{MQTT_TOPIC}'...")

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID,
                     protocol=mqtt.MQTTv5)  # Or mqtt.MQTTv5
client.on_connect = on_connect
client.on_disconnect = on_disconnect

try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()  # Start background thread for network traffic

    print(f"Publishing to topic: {MQTT_TOPIC}")
    for i in range(5):
        message = f"Hello from Docker Publisher! Message {i + 1} from Edmonton, AB"
        client.publish(MQTT_TOPIC, message, qos=2)  # Using QoS 1 for reliable delivery
        print(f"Published: '{message}'")
        time.sleep(2)

    print("Finished publishing messages. Disconnecting...")
    client.loop_stop()
    client.disconnect()

except Exception as e:
    print(f"An error occurred in publisher: {e}")
    if client:
        client.loop_stop()
        client.disconnect()
