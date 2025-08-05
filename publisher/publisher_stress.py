import os
import random
import sys
import threading
import time

import paho.mqtt.client as mqtt

# --- GLOBAL CONSTANTS (Configurable from Environment Variables) ---
NUM_PUBLISHER_CLIENTS = int(os.getenv('NUM_PUBLISHER_CLIENTS', 1))
NUM_MESSAGES_PER_CLIENT = int(os.getenv('NUM_MESSAGES_PER_CLIENT', 5))
MQTT_BROKER = os.getenv('MQTT_BROKER_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))
MQTT_TOPIC_BASE = os.getenv('MQTT_TOPIC_BASE', 'multi_client/test')
# -------------------------------------------------------------------

# List to hold client objects and their connection status
publisher_clients = []
client_connection_status = {}

# --- Global metrics counters ---
total_messages_published = 0
# A lock is needed to safely update the shared counter from multiple threads
messages_lock = threading.Lock()


# --- Callbacks for individual MQTT clients ---
def on_connect_factory(client_id_str):
    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            client_connection_status[client_id_str] = True
            print(f"Publisher Client '{client_id_str}': Connected successfully to {MQTT_BROKER}:{MQTT_PORT}!")
        else:
            client_connection_status[client_id_str] = False
            print(f"Publisher Client '{client_id_str}': Failed to connect, return code {rc}")

    return on_connect


def on_disconnect_factory(client_id_str):
    def on_disconnect(client, userdata, flags, rc, properties):
        client_connection_status[client_id_str] = False
        if rc != 0:
            print(f"Publisher Client '{client_id_str}': unexpectedly disconnected (RC: {rc}).")
        else:
            print(f"Publisher Client '{client_id_str}': Disconnected cleanly.")

    return on_disconnect


def publish_messages(client, client_id_str, topic, num_messages):
    global total_messages_published

    print(f"Publisher Client '{client_id_str}': Starting to publish {num_messages} messages to '{topic}'...")
    try:
        for i in range(num_messages):
            message_payload = f"Msg {i + 1} from '{client_id_str}' at {time.time()} (RND:{random.randint(0, 100000)})"
            result, mid = client.publish(topic, message_payload, qos=2)

            if result == mqtt.MQTT_ERR_SUCCESS:
                # Safely increment the global counter
                with messages_lock:
                    total_messages_published += 1

                if NUM_PUBLISHER_CLIENTS <= 2 or NUM_MESSAGES_PER_CLIENT <= 100:
                    print(f"Publisher Client '{client_id_str}': Sent: Topic='{topic}', Message='{message_payload}'")
                elif (i + 1) % 100 == 0 or (i + 1) == num_messages:
                    print(f"Publisher Client '{client_id_str}': Published {i + 1}/{num_messages} messages.")
            else:
                print(f"Publisher Client '{client_id_str}': Failed to publish message {i + 1}. Result: {result}")
    except Exception as e:
        print(f"Publisher Client '{client_id_str}': An error occurred during publishing: {e}")
    finally:
        time.sleep(2)
        client.loop_stop()
        client.disconnect()
        print(f"Publisher Client '{client_id_str}': Finished publishing and disconnected gracefully.")


def main():
    global total_messages_published

    print("--- Starting Multi-Client Publisher ---")
    print(f"Number of clients to spawn: {NUM_PUBLISHER_CLIENTS}")
    print(f"Messages per client: {NUM_MESSAGES_PER_CLIENT}")
    print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}, Base Topic: {MQTT_TOPIC_BASE}")
    print("---------------------------------------")

    threads = []

    # --- Start time for the entire test ---
    test_start_time = time.time()

    for i in range(NUM_PUBLISHER_CLIENTS):
        client_id_str = f"publisher_multi_{i + 1}_{os.getpid()}_{random.randint(1000, 9999)}"
        topic = f"{MQTT_TOPIC_BASE}/publisher_{i + 1}"
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=client_id_str,
                             protocol=mqtt.MQTTv5)
        client.on_connect = on_connect_factory(client_id_str)
        client.on_disconnect = on_disconnect_factory(client_id_str)
        publisher_clients.append(client)
        client_connection_status[client_id_str] = False

        print(f"Creating client '{client_id_str}' for topic '{topic}'...")
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_start()
        except Exception as e:
            print(f"Error connecting client '{client_id_str}': {e}")
            sys.exit(1)

    connect_start_time = time.time()
    while any(not status for status in client_connection_status.values()):
        print(f"Waiting for all {len(publisher_clients)} clients to connect...")
        time.sleep(1)
        if time.time() - connect_start_time > 30:
            print("Connection timeout for one or more clients. Proceeding with connected clients.")
            break

    for client in publisher_clients:
        client_id_from_paho = client._client_id.decode('utf-8')
        if client_connection_status.get(client_id_from_paho, False):
            t = threading.Thread(target=publish_messages, args=(client, client_id_from_paho,
                                                                f"{MQTT_TOPIC_BASE}/publisher_{client_id_from_paho.split('_')[2]}",
                                                                NUM_MESSAGES_PER_CLIENT))
            threads.append(t)
            t.start()
        else:
            print(f"Skipping publishing for disconnected client '{client_id_from_paho}'")

    for t in threads:
        t.join()

    # --- Calculate and report metrics ---
    test_end_time = time.time()
    test_duration = test_end_time - test_start_time
    total_messages = NUM_PUBLISHER_CLIENTS * NUM_MESSAGES_PER_CLIENT

    total_messages_published_final = total_messages_published

    average_publish_rate = 0
    if test_duration > 0:
        average_publish_rate = total_messages_published_final / test_duration

    print("\n--- Test Metrics Report ---")
    print(f"Total simulated clients: {NUM_PUBLISHER_CLIENTS}")
    print(f"Total messages published: {total_messages_published_final}/{total_messages}")
    print(f"Test duration: {test_duration:.2f} seconds")
    print(f"Average publish rate: {average_publish_rate:.2f} messages/second")
    print("----------------------------")

    print("--- All publisher clients finished. Exiting. ---")
    sys.exit(0)


if __name__ == "__main__":
    main()
