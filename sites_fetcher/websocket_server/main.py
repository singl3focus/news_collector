import asyncio
import json
import os
from typing import Dict, Set
import aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

app = FastAPI(title="News WebSocket Server")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        # source_id -> set of websocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # All connections regardless of source
        self.all_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, source_id: str = None):
        await websocket.accept()
        if source_id:
            if source_id not in self.active_connections:
                self.active_connections[source_id] = set()
            self.active_connections[source_id].add(websocket)
        self.all_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.all_connections.discard(websocket)
        for connections in self.active_connections.values():
            connections.discard(websocket)

    async def broadcast(self, message: str, source_id: str = None):
        """Broadcast message to all connections or specific source subscribers."""
        if source_id and source_id in self.active_connections:
            # Send to source-specific subscribers
            for connection in self.active_connections[source_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error sending to connection: {e}")
        else:
            # Send to all connections
            for connection in self.all_connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error sending to connection: {e}")

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, source: str = None):
    """WebSocket endpoint for client connections."""
    await manager.connect(websocket, source)
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

async def redis_listener():
    """Listen for new articles from Redis and broadcast to WebSocket clients."""
    redis = await aioredis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True
    )
    pubsub = redis.pubsub()
    await pubsub.subscribe("new_articles")

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message and message["type"] == "message":
                try:
                    article_data = json.loads(message["data"])
                    source_id = article_data.get("source")
                    await manager.broadcast(
                        json.dumps(article_data),
                        source_id
                    )
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode article data: {e}")
                except Exception as e:
                    logger.error(f"Error broadcasting article: {e}")
            await asyncio.sleep(0.1)
    except Exception as e:
        logger.error(f"Redis listener error: {e}")
    finally:
        await redis.close()

@app.on_event("startup")
async def startup_event():
    """Start Redis listener on application startup."""
    asyncio.create_task(redis_listener())

if __name__ == "__main__":
    import uvicorn
    logger.add("websocket.log", rotation="1 day")
    uvicorn.run(app, host="0.0.0.0", port=8000) 