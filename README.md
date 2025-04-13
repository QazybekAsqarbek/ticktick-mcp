# TickTick MCP (Management and Control Panel)

A system for managing and synchronizing TickTick data with MongoDB, providing a robust caching layer and API interface.

## System Architecture

The system consists of three main components:

1. **TickTick API Client** (`ticktick_api.py`)
   - Handles authentication and communication with the TickTick API
   - Implements rate limiting and retry mechanisms
   - Provides methods for fetching tasks, projects, and notes

2. **Database Layer** (`db.py`)
   - MongoDB-based storage with caching capabilities
   - Implements data validation and indexing
   - Handles data persistence with configurable cache durations

3. **Management Layer** (`manage_db.py`)
   - Orchestrates data synchronization between TickTick and MongoDB
   - Implements validation and error handling
   - Provides methods for syncing specific data types or all data

## Features

- **Rate Limiting**: Implements exponential backoff to handle API rate limits
- **Caching**: Stores data in MongoDB with configurable cache durations
- **Error Handling**: Comprehensive error handling and retry mechanisms
- **Data Validation**: Validates cached data before use
- **Batched Processing**: Processes data in batches to avoid overwhelming the API

## Setup

1. **Environment Variables**
   Create a `.env` file with the following variables:
   ```
   DIDA...
   MONGODB_URI=mongodb://admin:password@mongodb:27017/
   ```

2. **Docker Setup**
   ```bash
   docker-compose up -d
   ```

3. **Run the Sync Process**
   ```bash
   python manage_db.py
   ```

## Data Structure

### Projects
- ID
- Name
- Color
- Last Updated
- Cache Expiry

### Tasks
- ID
- Title
- Project ID
- Status
- Content
- Priority
- Start Date
- Due Date
- Last Updated
- Cache Expiry

### Notes
- ID
- Title
- Content
- Created Time
- Modified Time
- Last Updated
- Cache Expiry

## API Endpoints

The system provides the following API endpoints:

- `/tasks` - Get all tasks
- `/projects` - Get all projects
- `/notes` - Get all notes

## Error Handling

The system implements comprehensive error handling:
- Retries with exponential backoff for API calls
- Graceful degradation when cache is invalid
- Detailed logging of errors and operations

## Logging

Logs are stored in `/app/logs/ticktick_sync.log` and include:
- Operation timestamps
- Success/failure status
- Error messages
- Data counts and statistics

## Development

To contribute to the project:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License

