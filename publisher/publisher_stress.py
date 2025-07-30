import os
import random
import sys
import threading
import time

import paho.mqtt.client as mqtt

# --- GLOBAL CONSTANTS (Configurable from Environment Variables) ---
NUM_PUBLISHER_CLIENTS = int(os.getenv('NUM_PUBLISHER_CLIENTS', 1))  # Default to 1 client
NUM_MESSAGES_PER_CLIENT = int(os.getenv('NUM_MESSAGES_PER_CLIENT', 5))  # Default to 5 messages per client
MQTT_BROKER = os.getenv('MQTT_BROKER_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))
MQTT_TOPIC_BASE = os.getenv('MQTT_TOPIC_BASE', 'multi_client/test')  # Base topic for messages
# -------------------------------------------------------------------

# List to hold client objects and their connection status
publisher_clients = []
client_connection_status = {}  # client_id_str -> True/False


# --- Callbacks for individual MQTT clients ---
# The client_id here will be the *string* version we construct
def on_connect_factory(client_id_str):  # Renamed argument for clarity
    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            client_connection_status[client_id_str] = True  # Use the string ID
            print(f"Publisher Client '{client_id_str}': Connected successfully to {MQTT_BROKER}:{MQTT_PORT}!")
        else:
            client_connection_status[client_id_str] = False  # Use the string ID
            print(f"Publisher Client '{client_id_str}': Failed to connect, return code {rc}")
            # If a client fails to connect, it won't publish. The main loop will notice.

    return on_connect


def on_disconnect_factory(client_id_str):  # Renamed argument for clarity
    def on_disconnect(client, userdata, flags, rc, properties):
        client_connection_status[client_id_str] = False  # Use the string ID
        if rc != 0:
            print(f"Publisher Client '{client_id_str}': unexpectedly disconnected (RC: {rc}).")
        else:
            print(f"Publisher Client '{client_id_str}': Disconnected cleanly.")

    return on_disconnect


def publish_messages(client, client_id_str, topic, num_messages):  # client_id_str is already a string
    print(f"Publisher Client '{client_id_str}': Starting to publish {num_messages} messages to '{topic}'...")
    try:
        for i in range(num_messages):
            message_payload = f"Msg {i + 1} from '{client_id_str}' at {time.time()} (RND:{random.randint(0, 100000)})"
            # Publish with QoS 2
            result, mid = client.publish(topic, message_payload, qos=2)

            if result == mqtt.MQTT_ERR_SUCCESS:
                # --- MODIFIED LOGIC TO PRINT SENT MESSAGES ---
                # If NUM_PUBLISHER_CLIENTS is small (e.g., <= 2) or NUM_MESSAGES_PER_CLIENT is small (e.g., <= 100)
                # print every message for debugging. Otherwise, print periodically.
                if NUM_PUBLISHER_CLIENTS <= 2 or NUM_MESSAGES_PER_CLIENT <= 100:
                    print(f"Publisher Client '{client_id_str}': Sent: Topic='{topic}', Message='{message_payload}'")
                elif (i + 1) % 100 == 0 or (i + 1) == num_messages:
                    # Original periodic print for stress tests
                    print(f"Publisher Client '{client_id_str}': Published {i + 1}/{num_messages} messages.")
            else:
                print(f"Publisher Client '{client_id_str}': Failed to publish message {i + 1}. Result: {result}")
            # Optional: Add a small sleep to control publish rate if needed for specific tests
            # time.sleep(0.001)
    except Exception as e:
        print(f"Publisher Client '{client_id_str}': An error occurred during publishing: {e}")
    finally:
        # Give a short moment for any final QoS 2 ACKs
        time.sleep(2)
        client.loop_stop()
        client.disconnect()
        print(f"Publisher Client '{client_id_str}': Finished publishing and disconnected gracefully.")


def main():
    print(f"--- Starting Multi-Client Publisher ---")
    print(f"Number of clients to spawn: {NUM_PUBLISHER_CLIENTS}")
    print(f"Messages per client: {NUM_MESSAGES_PER_CLIENT}")
    print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}, Base Topic: {MQTT_TOPIC_BASE}")
    print("---------------------------------------")

    threads = []
    for i in range(NUM_PUBLISHER_CLIENTS):
        # Construct the client ID as a string immediately
        client_id_str = f"publisher_multi_{i + 1}_{os.getpid()}_{random.randint(1000, 9999)}"
        topic = f"{MQTT_TOPIC_BASE}/publisher_{i + 1}"  # Unique topic for each logical publisher

        # Pass the string client_id_str to the MQTT client constructor
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=client_id_str,
                             protocol=mqtt.MQTTv5)
        client.on_connect = on_connect_factory(client_id_str)
        client.on_disconnect = on_disconnect_factory(client_id_str)
        publisher_clients.append(client)
        client_connection_status[client_id_str] = False  # Initialize connection status with string ID

        print(f"Creating client '{client_id_str}' for topic '{topic}'...")
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)  # Connect with 60-second keepalive
            client.loop_start()  # Start a separate thread for each client's network loop
        except Exception as e:
            print(f"Error connecting client '{client_id_str}': {e}")
            sys.exit(1)  # Exit if initial connection attempt fails for a client

    # Wait for all clients to connect
    connect_start_time = time.time()
    # Check status using the string client_id_str
    while any(not status for status in client_connection_status.values()):
        print(f"Waiting for all {len(publisher_clients)} clients to connect...")
        time.sleep(1)
        if time.time() - connect_start_time > 30:  # Timeout after 30 seconds
            print("Connection timeout for one or more clients. Proceeding with connected clients.")
            break

    # Start publishing threads for each connected client
    for client in publisher_clients:
        # Use client._client_id.decode('utf-8') to get the string representation
        # of the client ID provided by paho-mqtt, which is a bytes object.
        # This ensures the key matches what's used in client_connection_status.
        client_id_from_paho = client._client_id.decode('utf-8')
        if client_connection_status.get(client_id_from_paho, False):
            # Pass the string client_id_from_paho to the publishing thread
            t = threading.Thread(target=publish_messages, args=(client, client_id_from_paho,
                                                                f"{MQTT_TOPIC_BASE}/publisher_{client_id_from_paho.split('_')[2]}",
                                                                # Extract instance number for topic
                                                                NUM_MESSAGES_PER_CLIENT))
            threads.append(t)
            t.start()
        else:
            print(f"Skipping publishing for disconnected client '{client_id_from_paho}'")

    # Wait for all publishing threads to complete
    for t in threads:
        t.join()

    print("--- All publisher clients finished. Exiting. ---")
    sys.exit(0)


if __name__ == "__main__":
    main()
