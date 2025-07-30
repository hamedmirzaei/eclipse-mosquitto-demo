import os
import random
import sys
import threading
import time

import paho.mqtt.client as mqtt

# --- GLOBAL CONSTANTS (Configurable from Environment Variables) ---
NUM_SUBSCRIBER_CLIENTS = int(os.getenv('NUM_SUBSCRIBER_CLIENTS', 1))  # Default to 1 client
SUBSCRIBER_DURATION_SECONDS = int(os.getenv('SUBSCRIBER_DURATION_SECONDS', 60))  # Default 60s
MQTT_BROKER = os.getenv('MQTT_BROKER_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))
MQTT_TOPIC_WILDCARD = os.getenv('MQTT_TOPIC_WILDCARD', 'multi_client/#')  # Wildcard for all messages
# -------------------------------------------------------------------

# Dictionary to hold message counts per subscriber client
messages_received_per_client = {}  # client_id_str -> count
client_connection_status = {}  # client_id_str -> True/False
subscriber_clients = []

# Global event to signal all subscriber threads to stop
STOP_EVENT = threading.Event()


# --- Callbacks for individual MQTT clients ---
def on_connect_factory(client_id_str, topic):
    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            client_connection_status[client_id_str] = True
            print(f"Subscriber Client '{client_id_str}': Connected successfully to {MQTT_BROKER}:{MQTT_PORT}!")
            client.subscribe(topic, qos=2)
            print(f"Subscriber Client '{client_id_str}': Listening on topic: {topic}")
        else:
            client_connection_status[client_id_str] = False
            print(f"Subscriber Client '{client_id_str}': Failed to connect, return code {rc}. Will try to reconnect.")

    return on_connect


def on_message_factory(client_id_str):
    def on_message(client, userdata, msg):
        messages_received_per_client[client_id_str] = messages_received_per_client.get(client_id_str, 0) + 1

        try:
            payload = msg.payload.decode('utf-8')
        except UnicodeDecodeError:
            payload = f"<undecodable bytes: {msg.payload}>"

        # --- MODIFIED LOGIC TO PRINT MESSAGES ---
        # If NUM_MESSAGES_PER_CLIENT is small (e.g., <= 100), print every message for debugging
        # Otherwise, print periodically for stress tests
        # Assuming NUM_MESSAGES_PER_CLIENT from publisher is available, which it isn't directly here.
        # A better heuristic for "low message count" from subscriber side is to check if total received is low.
        # Or, ideally, pass a global debug flag through environment.

        # Option 1: Print every message if total clients is low (e.g., 1 or 2)
        # This is a good heuristic if you're not passing explicit "debug_print" flags
        if NUM_SUBSCRIBER_CLIENTS <= 2:  # Adjust this threshold as needed
            print(
                f"Subscriber Client '{client_id_str}': Received: Topic='{msg.topic}', Message='{payload}' (QoS: {msg.qos}, Retain: {msg.retain})")
        else:
            # Option 2: Periodic printing for stress tests
            if messages_received_per_client[client_id_str] % 1000 == 0:
                current_time = time.time()
                elapsed = current_time - (client.userdata.get('start_time', current_time))
                rate = messages_received_per_client[client_id_str] / elapsed if elapsed > 0 else 0
                print(
                    f"Subscriber Client '{client_id_str}': Received {messages_received_per_client[client_id_str]} messages. Rate: {rate:.2f} msg/s.")
        # --- END MODIFIED LOGIC ---

    return on_message


def on_disconnect_factory(client_id_str):
    def on_disconnect(client, userdata, flags, rc, properties):
        client_connection_status[client_id_str] = False
        if rc != 0:
            print(
                f"Subscriber Client '{client_id_str}': Unexpectedly disconnected (RC: {rc}). Loop will try to reconnect.")
        else:
            print(f"Subscriber Client '{client_id_str}': Disconnected cleanly.")

    return on_disconnect


def subscriber_loop(client, client_id_str, duration):
    client.userdata = {'start_time': time.time()}
    client.loop_start()

    print(f"Subscriber Client '{client_id_str}': Will listen for {duration} seconds...")
    STOP_EVENT.wait(duration)

    print(f"Subscriber Client '{client_id_str}': Listener duration elapsed. Disconnecting...")
    client.loop_stop()
    client.disconnect()
    print(
        f"Subscriber Client '{client_id_str}': Disconnected. Total messages received: {messages_received_per_client.get(client_id_str, 0)}")


def main():
    print(f"--- Starting Multi-Client Subscriber ---")
    print(f"Number of clients to spawn: {NUM_SUBSCRIBER_CLIENTS}")
    print(f"Listen duration per client: {SUBSCRIBER_DURATION_SECONDS} seconds")
    print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}, Topic: {MQTT_TOPIC_WILDCARD}")
    print("---------------------------------------")

    threads = []
    for i in range(NUM_SUBSCRIBER_CLIENTS):
        client_id_str = f"subscriber_multi_{i + 1}_{os.getpid()}_{random.randint(1000, 9999)}"

        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=client_id_str,
                             protocol=mqtt.MQTTv5)
        client.on_connect = on_connect_factory(client_id_str, MQTT_TOPIC_WILDCARD)
        client.on_message = on_message_factory(client_id_str)
        client.on_disconnect = on_disconnect_factory(client_id_str)
        subscriber_clients.append(client)
        messages_received_per_client[client_id_str] = 0
        client_connection_status[client_id_str] = False

        print(f"Creating client '{client_id_str}'...")
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_start()
        except Exception as e:
            print(f"Error connecting client '{client_id_str}': {e}")
            sys.exit(1)

    connect_start_time = time.time()
    while any(not status for status in client_connection_status.values()):
        print(f"Waiting for all {len(subscriber_clients)} clients to connect...")
        time.sleep(1)
        if time.time() - connect_start_time > 30:
            print("Connection timeout for one or more clients. Proceeding with connected clients.")
            break

    for client in subscriber_clients:
        client_id_from_paho = client._client_id.decode('utf-8')
        if client_connection_status.get(client_id_from_paho, False):
            t = threading.Thread(target=subscriber_loop,
                                 args=(client, client_id_from_paho, SUBSCRIBER_DURATION_SECONDS))
            threads.append(t)
            t.start()
        else:
            print(f"Skipping listening for disconnected client '{client_id_from_paho}'")

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt detected. Signaling threads to stop...")
        STOP_EVENT.set()
        for t in threads:
            t.join(timeout=5)
        print("All subscriber clients stopped.")

    final_total_messages = sum(messages_received_per_client.values())
    print(f"--- All subscriber clients finished. Final Total Messages Received: {final_total_messages}. Exiting. ---")
    sys.exit(0)


if __name__ == "__main__":
    main()
