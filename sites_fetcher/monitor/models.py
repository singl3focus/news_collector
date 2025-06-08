from typing import Optional, List
from pydantic import BaseModel, HttpUrl
from datetime import datetime

class Source(BaseModel):
    id: str
    type: str  # html or rss
    url: HttpUrl
    selector: Optional[str] = None
    title_selector: Optional[str] = None
    interval: int  # seconds
    parser_module: Optional[str] = None

class SourcesConfig(BaseModel):
    sources: List[Source]

class Article(BaseModel):
    source_id: str
    title: str
    url: HttpUrl
    timestamp: datetime = datetime.utcnow()

    def to_websocket_event(self) -> dict:
        return {
            "event": "new_article",
            "source": self.source_id,
            "title": self.title,
            "url": str(self.url),
            "timestamp": self.timestamp.isoformat()
        }

class ChroxySession(BaseModel):
    id: str
    ws_url: str
    browser_url: str 