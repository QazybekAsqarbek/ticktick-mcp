#!/bin/bash

# Check if containers are running
if ! docker-compose --env-file .env ps | grep -q "Up"; then
    echo "Containers are not running. Starting them..."
    docker-compose --env-file .env up -d
    sleep 5  # Wait for containers to start
fi

# Enter MongoDB shell and run queries
echo "Entering MongoDB shell..."
docker-compose --env-file .env exec mongodb mongosh -u admin -p password --eval '
    // Show all databases
    print("\nDatabases:");
    printjson(db.adminCommand("listDatabases"));
    
    // Use the current database
    db = db.getSiblingDB("ticktick_mcp");
    
    // Show all collections
    print("\nCollections:");
    printjson(db.getCollectionNames());
    
    // Count documents in each collection
    print("\nDocument counts:");
    db.getCollectionNames().forEach(function(collection) {
        print(collection + ": " + db[collection].countDocuments());
    });
    
    // Show tasks per project
    print("\nTasks per project:");
    db.projects.find().forEach(function(project) {
        var taskCount = db.tasks.countDocuments({projectId: project.id});
        print("Project \"" + project.name + "\" (ID: " + project.id + "): " + taskCount + " tasks");
    });
    
    // Show recent tasks
    print("\nRecent tasks (last 5):");
    db.tasks.find().sort({last_updated: -1}).limit(5).forEach(function(task) {
        var project = db.projects.findOne({id: task.projectId});
        var projectName = project ? project.name : "Unknown Project";
        print("Task: " + task.title + " (Project: " + projectName + ")");
        print("  Last Updated: " + task.last_updated);
        print("  Cache Expires: " + task.cache_expiry);
        print("---");
    });
' 