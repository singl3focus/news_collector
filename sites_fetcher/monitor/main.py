import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Set
import aioredis
from loguru import logger
from .models import Source, SourcesConfig, Article
from .chroxy_client import ChroxyClient

class NewsMonitor:
    def __init__(self, redis_url: str, chroxy_url: str, sources_file: str):
        self.redis_url = redis_url
        self.chroxy_url = chroxy_url
        self.sources_file = sources_file
        self.chroxy = ChroxyClient(chroxy_url)
        self.redis = None
        self.sources: Dict[str, Source] = {}
        self.last_check: Dict[str, datetime] = {}
        self.running = False

    async def init(self):
        """Initialize connections and load sources."""
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        await self.load_sources()

    async def load_sources(self):
        """Load sources from configuration file."""
        try:
            with open(self.sources_file) as f:
                config = SourcesConfig.parse_obj(json.load(f))
                self.sources = {source.id: source for source in config.sources}
                logger.info(f"Loaded {len(self.sources)} sources")
        except Exception as e:
            logger.error(f"Failed to load sources: {e}")
            raise

    async def get_article_key(self, source_id: str, article_hash: str) -> str:
        """Generate Redis key for an article."""
        return f"article:{source_id}:{article_hash}"

    async def is_new_article(self, source_id: str, article: Article) -> bool:
        """Check if article is new by comparing with Redis."""
        article_hash = f"{article.title}:{article.url}"
        key = await self.get_article_key(source_id, article_hash)
        
        exists = await self.redis.exists(key)
        if not exists:
            # Store article with 24h TTL
            await self.redis.set(key, article.json(), ex=86400)
            return True
        return False

    async def process_source(self, source: Source):
        """Process a single news source."""
        try:
            if source.type == "html":
                session = await self.chroxy.create_session()
                try:
                    articles_data = await self.chroxy.navigate_and_extract(
                        session.id, str(source.url), source.selector
                    )
                    
                    for article_data in articles_data:
                        article = Article(
                            source_id=source.id,
                            title=article_data['title'],
                            url=article_data['url']
                        )
                        
                        if await self.is_new_article(source.id, article):
                            # Publish to Redis for websocket server
                            await self.redis.publish(
                                "new_articles",
                                article.to_websocket_event()
                            )
                            logger.info(f"New article found: {article.title}")
                
                finally:
                    await self.chroxy.close_session(session.id)
            
            elif source.type == "rss":
                # TODO: Implement RSS feed processing
                pass
                
        except Exception as e:
            logger.error(f"Error processing source {source.id}: {e}")

    async def monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            tasks = []
            current_time = datetime.utcnow()
            
            for source_id, source in self.sources.items():
                last_check = self.last_check.get(source_id)
                if not last_check or (current_time - last_check).total_seconds() >= source.interval:
                    tasks.append(self.process_source(source))
                    self.last_check[source_id] = current_time
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            await asyncio.sleep(1)  # Prevent tight loop

    async def start(self):
        """Start the monitoring service."""
        self.running = True
        await self.init()
        logger.info("Starting news monitor service")
        await self.monitor_loop()

    async def stop(self):
        """Stop the monitoring service."""
        self.running = False
        await self.chroxy.close()
        if self.redis:
            await self.redis.close()

async def main():
    """Entry point for the monitor service."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    chroxy_url = os.getenv("CHROXY_URL", "http://localhost:9222")
    sources_file = os.getenv("SOURCES_FILE", "sources.json")
    
    monitor = NewsMonitor(redis_url, chroxy_url, sources_file)
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Shutting down monitor service")
        await monitor.stop()

if __name__ == "__main__":
    logger.add("monitor.log", rotation="1 day")
    asyncio.run(main()) 