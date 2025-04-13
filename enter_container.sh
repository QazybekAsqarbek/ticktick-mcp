#!/bin/bash

# Check for .env file
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)


# Function to check if containers are running
check_containers() {
    if docker-compose --env-file .env ps | grep -q "Up"; then
        return 0
    else
        return 1
    fi
}

# Function to stop containers
stop_containers() {
    echo "Stopping existing containers..."
    docker-compose --env-file .env down
}

# Function to start containers
start_containers() {
    echo "Starting containers..."
    docker-compose --env-file .env up -d
}

# Function to enter container
enter_container() {
    echo "Entering container..."
    docker-compose --env-file .env exec app bash
}

# Function to sync data
sync_data() {
    echo "Syncing data from TickTick..."
    docker-compose --env-file .env exec app python -c "import asyncio; from manage_db import main; asyncio.run(main())"
}

# Main script
echo "TickTick MCP Container Manager"

# Check if containers are running
if check_containers; then
    read -p "Containers are already running. Do you want to restart them? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        stop_containers
        start_containers
        # After restart, sync data
        sync_data
    fi
else
    start_containers
    # After starting, sync data
    sync_data
fi

# Enter the container
enter_container 