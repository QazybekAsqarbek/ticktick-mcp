#!/bin/bash

# Wait for MongoDB to be ready
echo "Waiting for MongoDB to be ready..."
until python -c "import pymongo; pymongo.MongoClient('mongodb://admin:password@mongodb:27017/').admin.command('ping')" &> /dev/null; do
    echo "MongoDB is unavailable - sleeping"
    sleep 1
done

echo "MongoDB is up - starting MCP interface"

# Start the MCP interface
python mcp_interface.py 