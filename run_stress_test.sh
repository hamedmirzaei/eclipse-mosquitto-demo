#!/bin/bash

# Configuration for the MQTT setup
# Default values for a simple demo
NUM_PUBLISHER_CLIENTS=${1:-1}         # Default to 1 MQTT client in the publisher container
NUM_MESSAGES_PER_CLIENT=${2:-5}       # Default to 5 messages per MQTT client
NUM_SUBSCRIBER_CLIENTS=${3:-1}        # Default to 1 MQTT client in the subscriber container
SUBSCRIBER_DURATION_SECONDS=${4:-60} # Default to subscribers listening for 60 seconds
MQTT_TOPIC_BASE=${5:-multi_client/test} # Default base topic

echo "--- MQTT Multi-Client Demo/Scalability Test Configuration ---"
echo "Publisher Container will spawn: ${NUM_PUBLISHER_CLIENTS} MQTT clients"
echo "Each Publisher client sends: ${NUM_MESSAGES_PER_CLIENT} messages"
echo "Subscriber Container will spawn: ${NUM_SUBSCRIBER_CLIENTS} MQTT clients"
echo "Each Subscriber client listens for: ${SUBSCRIBER_DURATION_SECONDS} seconds"
echo "MQTT Base Topic: ${MQTT_TOPIC_BASE}"
echo "----------------------------------------------------"
echo ""

# Ensure Docker Compose is available
if ! command -v docker-compose &> /dev/null
then
    echo "docker-compose could not be found. Please install Docker Compose."
    exit 1
fi

# 1. Stop and remove any previous containers from this project
echo "Stopping and removing previous containers..."
docker-compose -f ./docker-compose.stress.yml down --remove-orphans

# 2. Build images (if needed) and bring up services based on environment variables
echo "Building images and starting services..."
# Pass environment variables directly to docker-compose
NUM_PUBLISHER_CLIENTS=${NUM_PUBLISHER_CLIENTS} \
NUM_MESSAGES_PER_CLIENT=${NUM_MESSAGES_PER_CLIENT} \
NUM_SUBSCRIBER_CLIENTS=${NUM_SUBSCRIBER_CLIENTS} \
SUBSCRIBER_DURATION_SECONDS=${SUBSCRIBER_DURATION_SECONDS} \
MQTT_TOPIC_BASE=${MQTT_TOPIC_BASE} \
docker-compose -f ./docker-compose.stress.yml up --build -d

echo ""
echo "--- Services started ---"
echo "Mosquitto Broker: tcp://localhost:1883"
echo "Node-RED Dashboard: http://localhost:1880"
echo "Access Node-RED dashboard at http://localhost:1880/ui to see data (after configuring MQTT In node to subscribe to ${MQTT_TOPIC_BASE}/#)."
echo ""
echo "Check container logs: docker-compose logs -f"

# Wait for publishers and subscribers to complete their tasks
# The time for this is the SUBSCRIBER_DURATION_SECONDS + a buffer
# The Python scripts themselves handle their duration and exit.
TOTAL_TEST_DURATION=$((SUBSCRIBER_DURATION_SECONDS + 10)) # Add a 10-second buffer
echo "Test will run for approximately ${TOTAL_TEST_DURATION} seconds. Waiting..."
sleep ${TOTAL_TEST_DURATION}

echo ""
echo "--- Test Duration Elapsed. Collecting final reports and logs. ---"

# Display logs for all services to see summary reports from clients
docker-compose -f ./docker-compose.stress.yml logs --tail 200 # Show last 200 lines of logs

echo ""
echo "--- Cleaning up containers ---"
docker-compose -f ./docker-compose.stress.yml down --remove-orphans

echo "Test finished."