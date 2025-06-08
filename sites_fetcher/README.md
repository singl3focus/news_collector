# News Socket Proxy

A real-time news monitoring system that uses headless Chrome (via chroxy) to monitor news websites and distribute updates via WebSocket.

## Features

- Monitor multiple news sources (HTML and RSS)
- Real-time updates via WebSocket
- Source-specific subscriptions
- Automatic deduplication of articles
- Scalable architecture with Redis for state management
- Docker-based deployment

## Architecture

The system consists of several components:

1. **chroxy**: A pool of headless Chrome instances
2. **monitor**: Python service that monitors news sources
3. **websocket**: FastAPI server for real-time updates
4. **redis**: State management and pub/sub

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd sites_fetcher
```

2. Create a `sources.json` file with your news sources:
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

3. Start the services:
```bash
docker-compose up -d
```

## Usage

### WebSocket Client

Connect to the WebSocket server:

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

### Article Format

```json
{
  "event": "new_article",
  "source": "rbc",
  "title": "Article Title",
  "url": "https://example.com/article",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Adding New Sources

1. Edit `sources.json` to add a new source:
```json
{
  "id": "new_source",
  "type": "html",
  "url": "https://example.com/news",
  "selector": ".article-link",
  "interval": 30
}
```

2. The monitor service will automatically pick up the new source on the next check.

## Development

### Local Development

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run services individually:
```bash
# Terminal 1: Monitor service
python -m monitor.main

# Terminal 2: WebSocket server
python -m websocket_server.main
```

### Environment Variables

- `REDIS_URL`: Redis connection URL (default: redis://localhost:6379/0)
- `CHROXY_URL`: chroxy service URL (default: http://localhost:9222)
- `SOURCES_FILE`: Path to sources.json (default: sources.json)

## Monitoring

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

MIT License 