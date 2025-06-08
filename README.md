# News Collector Platform

A comprehensive platform for collecting and monitoring news from multiple sources, including Telegram channels and news websites. The platform consists of two main services that work together to provide real-time news aggregation and delivery.

## Overview

The platform consists of two main services:

1. **Telegram Fetcher Service**: Monitors and collects messages from Telegram channels
2. **News Socket Proxy**: Monitors news websites and RSS feeds

Both services provide real-time updates via WebSocket interfaces and can be used independently or together.

## Features

### Telegram Fetcher Service
- 📡 Real-time message collection from Telegram channels
- 🔄 Automatic channel subscription management
- 🌐 REST API for channel management
- 🔌 WebSocket interface for real-time message delivery
- 🔒 Rate limiting and security features
- 📊 Multiple Telegram client support for load balancing
- 💾 Simple JSON-based channel storage
- 🧪 Built-in API testing tools

### News Socket Proxy
- 📰 Monitor multiple news sources (HTML and RSS)
- 🔄 Real-time updates via WebSocket
- 🎯 Source-specific subscriptions
- 🔍 Automatic deduplication of articles
- 📈 Scalable architecture with Redis
- 🐳 Docker-based deployment
- 🌐 Headless Chrome support via chroxy

## Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose (for News Socket Proxy)
- Telegram API credentials (for Telegram Fetcher)
- Redis (for News Socket Proxy)
- Virtual environment (recommended)
- `jq` for JSON processing (for testing)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd news_collector
```

### 2. Set Up Telegram Fetcher Service

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root:
```env
# Telegram API credentials
API_ID_1=your_first_api_id
API_HASH_1=your_first_api_hash
SESSION_NAME_1=client1

API_ID_2=your_second_api_id
API_HASH_2=your_second_api_hash
SESSION_NAME_2=client2

JSONDB_API_URL=http://localhost:8001/api/channels
```

### 3. Set Up News Socket Proxy

1. Create a `sites_fetcher/sources.json` file:
```json
{
  "sources": [
    {
      "id": "rbc",
      "type": "html",
      "url": "https://www.rbc.ru/",
      "selector": ".main__feed .item__link",
      "title_selector": ".item__title",
      "interval": 20
    }
  ]
}
```

2. Start the services using Docker Compose:
```bash
cd sites_fetcher
docker-compose up -d
```

## Running the Services

### Telegram Fetcher Service

1. Start the REST API server:
```bash
uvicorn telegram_fetcher.main:app --host 0.0.0.0 --port 8001
```

2. The Telegram client workers and WebSocket server will start automatically.

### News Socket Proxy

The service runs in Docker containers. To start:
```bash
cd sites_fetcher
docker-compose up -d
```

## API Documentation

### Telegram Fetcher API

#### REST Endpoints

1. **Get All Channels**
```http
GET /api/channels
```

2. **Add Channel**
```http
POST /api/add_channel
Content-Type: application/json

{
    "link": "https://t.me/channel_name"
}
```

3. **Get Channel ID**
```http
GET /api/channel_id/{link}
```

4. **Delete Channel**
```http
DELETE /api/channels/{link}
```

#### WebSocket Interface
```javascript
const ws = new WebSocket('ws://localhost:8001/ws');

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('New message:', message);
};
```

### News Socket Proxy API

#### WebSocket Interface
```javascript
// Connect to all sources
const ws = new WebSocket('ws://localhost:8000/ws');

// Or connect to a specific source
const ws = new WebSocket('ws://localhost:8000/ws?source=rbc');

ws.onmessage = (event) => {
    const article = JSON.parse(event.data);
    console.log('New article:', article);
};
```

## Message Formats

### Telegram Messages
```json
{
    "timestamp": "2024-03-14T12:00:00Z",
    "channel_id": 123456789,
    "channel_title": "Channel Name",
    "text": "Message content"
}
```

### News Articles
```json
{
    "event": "new_article",
    "source": "rbc",
    "title": "Article Title",
    "url": "https://example.com/article",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

## Development

### Project Structure
```
news_collector/
├── telegram_fetcher/          # Telegram monitoring service
│   ├── main.py               # Main service entry point
│   ├── jsondb.py             # JSON-based channel storage
│   ├── jsondb_api.py         # REST API implementation
│   ├── tg_client_pool.py     # Telegram client management
│   ├── tg_config.py          # Configuration and credentials
│   └── tests/                # Test suite
│
└── sites_fetcher/            # News website monitoring service
    ├── monitor/              # News monitoring service
    ├── websocket_server/     # WebSocket server
    ├── sources.json          # News source configuration
    ├── docker-compose.yml    # Docker configuration
    └── requirements.txt      # Python dependencies
```

### Running Tests

1. Telegram Fetcher tests:
```bash
# Run API tests
./telegram_fetcher/test_api.sh

# Run unit tests
pytest telegram_fetcher/tests/
```

2. News Socket Proxy tests:
```bash
cd sites_fetcher
pytest tests/
```

## Security Considerations

1. Store API credentials securely in `.env` files
2. Both services implement rate limiting
3. CORS middleware is configured
4. WebSocket connections are validated
5. Redis is protected by password (in production)

## Monitoring

### Telegram Fetcher
- API logs: Available through uvicorn logging
- WebSocket connection status: Available through the API
- Channel status: Available through the API

### News Socket Proxy
- Monitor service logs: `monitor.log`
- WebSocket server logs: `websocket.log`
- Redis state: Use Redis CLI to inspect article keys

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License.

## Support

For issues and feature requests, please create an issue in the repository. 