#!/bin/bash

# Ensure Docker Compose is available
if ! command -v docker-compose &> /dev/null
then
    echo "docker-compose could not be found. Please install Docker Compose."
    exit 1
fi

# 1. Stop and remove any previous containers from this project
echo "Stopping and removing previous containers..."
docker-compose -f ./docker-compose.yml down --remove-orphans

# 2. Build images (if needed) and bring up services based on environment variables
echo "Building images and starting services..."

docker-compose -f ./docker-compose.yml up --build -d

echo ""
echo "--- Services started ---"
echo "Mosquitto Broker: tcp://localhost:1883"
echo "Node-RED Dashboard: http://localhost:1880"
echo "Access Node-RED dashboard at http://localhost:1880/ui to see data (after configuring MQTT In node to subscribe to /#)."
echo ""
echo "Check container logs: docker-compose logs -f"

# Wait for publishers and subscribers to complete their tasks
# The time for this is the SUBSCRIBER_DURATION_SECONDS + a buffer
# The Python scripts themselves handle their duration and exit.
TOTAL_TEST_DURATION=$((70)) # Add a 10-second buffer
echo "Test will run for approximately ${TOTAL_TEST_DURATION} seconds. Waiting..."
sleep ${TOTAL_TEST_DURATION}

echo ""
echo "--- Test Duration Elapsed. Collecting final reports and logs. ---"

# Display logs for all services to see summary reports from clients
docker-compose -f ./docker-compose.yml logs --tail 200 # Show last 200 lines of logs

echo ""
echo "--- Cleaning up containers ---"
docker-compose -f ./docker-compose.yml down --remove-orphans

echo "Test finished."