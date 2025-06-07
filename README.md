# Telegram Fetcher Service

A robust service for monitoring and collecting messages from Telegram channels. The service provides a REST API for channel management and a WebSocket interface for real-time message delivery.

## Features

- 📡 Real-time message collection from Telegram channels
- 🔄 Automatic channel subscription management
- 🌐 REST API for channel management
- 🔌 WebSocket interface for real-time message delivery
- 🔒 Rate limiting and security features
- 📊 Multiple Telegram client support for load balancing
- 💾 Simple JSON-based channel storage
- 🧪 Built-in API testing tools

## Prerequisites

- Python 3.10 or higher
- Telegram API credentials (API ID and API Hash)
- Virtual environment (recommended)
- `jq` for JSON processing (for testing)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd news_collector
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with your Telegram API credentials:
```env
API_ID_1=your_first_api_id
API_HASH_1=your_first_api_hash
SESSION_NAME_1=client1

API_ID_2=your_second_api_id
API_HASH_2=your_second_api_hash
SESSION_NAME_2=client2

JSONDB_API_URL=http://localhost:8001/api/channels
```

5. Install `jq` for JSON processing (required for testing):
```bash
# On macOS:
brew install jq

# On Ubuntu/Debian:
sudo apt-get install jq

# On Windows (with Chocolatey):
choco install jq
```

## Running the Service

The service consists of two main components:

1. REST API server (for channel management):
```bash
uvicorn telegram_fetcher.main:app --host 0.0.0.0 --port 8001
```

2. Telegram client workers and WebSocket server (automatically started with the main service)

## API Documentation

### REST API Endpoints

#### Get All Channels
```http
GET /api/channels
```
Returns a list of all monitored channels with their current status.

Response example:
```json
[
    {
        "link": "https://t.me/channel_name",
        "title": "Channel Title",
        "status": "connected"
    }
]
```

#### Add Channel
```http
POST /api/add_channel
Content-Type: application/json

{
    "link": "https://t.me/channel_name"
}
```

Response example:
```json
{
    "ok": true,
    "status": "pending",
    "message": "Channel added, connection in progress"
}
```

#### Get Channel ID
```http
GET /api/channel_id/{link}
```
Returns channel information including its Telegram ID.

Response example:
```json
{
    "ok": true,
    "channel_id": 123456789,
    "username": "channel_name",
    "title": "Channel Title",
    "type": "channel"
}
```

#### Delete Channel
```http
DELETE /api/channels/{link}
```

Response example:
```json
{
    "ok": true
}
```

### WebSocket Interface

Connect to the WebSocket endpoint to receive real-time messages:
```javascript
const ws = new WebSocket('ws://localhost:8001/ws');

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('New message:', message);
};
```

Message format:
```json
{
    "timestamp": "2024-03-14T12:00:00Z",
    "channel_id": 123456789,
    "channel_title": "Channel Name",
    "text": "Message content"
}
```

## Testing the API

The repository includes a test script (`test_api.sh`) that demonstrates the usage of all API endpoints. To run the tests:

1. Make sure the service is running
2. Make the test script executable:
```bash
chmod +x test_api.sh
```
3. Run the tests:
```bash
./test_api.sh
```

The test script includes:
- Getting the list of channels
- Adding a new channel
- Getting channel ID
- Deleting a channel
- Testing rate limiting

## Rate Limiting

The service implements rate limiting to prevent abuse:
- Window: 60 seconds
- Maximum requests: 100 per window
- Rate limit headers are included in responses
- Returns 429 status code when limit is exceeded

## Security Considerations

1. Store your Telegram API credentials securely in the `.env` file
2. The service uses CORS middleware (configured for development)
3. Rate limiting is enabled by default
4. WebSocket connections are validated
5. All API endpoints are protected by rate limiting

## Development

### Project Structure
```
telegram_fetcher/
├── main.py           # Main service entry point
├── jsondb.py         # JSON-based channel storage
├── jsondb_api.py     # REST API implementation
├── tg_client_pool.py # Telegram client management
├── tg_config.py      # Configuration and credentials
├── test_api.sh       # API testing script
└── tests/            # Test suite
```

### Running Tests
```bash
# Run API tests
./test_api.sh

# Run unit tests
pytest telegram_fetcher/tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the terms of the license included in the repository.

## Support

For issues and feature requests, please create an issue in the repository. 