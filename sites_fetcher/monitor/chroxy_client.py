import json
import asyncio
from typing import Optional, Dict, Any
import httpx
from loguru import logger
from .models import ChroxySession

class ChroxyClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self._sessions: Dict[str, ChroxySession] = {}

    async def create_session(self) -> ChroxySession:
        """Create a new Chrome session via chroxy."""
        try:
            response = await self.client.post(f"{self.base_url}/json/new")
            response.raise_for_status()
            data = response.json()
            
            session = ChroxySession(
                id=data['id'],
                ws_url=data['webSocketDebuggerUrl'],
                browser_url=data['browserWSEndpoint']
            )
            self._sessions[session.id] = session
            return session
        except Exception as e:
            logger.error(f"Failed to create chroxy session: {e}")
            raise

    async def close_session(self, session_id: str) -> None:
        """Close a Chrome session."""
        if session_id in self._sessions:
            try:
                await self.client.delete(f"{self.base_url}/json/close/{session_id}")
                del self._sessions[session_id]
            except Exception as e:
                logger.error(f"Failed to close chroxy session {session_id}: {e}")
                raise

    async def execute_cdp(self, session_id: str, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a Chrome DevTools Protocol command."""
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self._sessions[session_id]
        try:
            async with httpx.AsyncClient() as client:
                async with client.ws_connect(session.ws_url) as websocket:
                    message = {
                        "id": 1,
                        "method": method,
                        "params": params or {}
                    }
                    await websocket.send(json.dumps(message))
                    response = await websocket.receive_text()
                    return json.loads(response)
        except Exception as e:
            logger.error(f"CDP command failed for session {session_id}: {e}")
            raise

    async def navigate_and_extract(self, session_id: str, url: str, selector: str) -> list:
        """Navigate to URL and extract elements using selector."""
        try:
            # Navigate to page
            await self.execute_cdp(session_id, "Page.enable")
            await self.execute_cdp(session_id, "Page.navigate", {"url": url})
            
            # Wait for network idle
            await asyncio.sleep(2)  # Basic wait, could be improved with proper network idle detection
            
            # Extract elements
            result = await self.execute_cdp(
                session_id,
                "Runtime.evaluate",
                {
                    "expression": f"""
                    Array.from(document.querySelectorAll('{selector}')).map(el => {{
                        return {{
                            title: el.textContent.trim(),
                            url: el.href || el.getAttribute('href')
                        }}
                    }})
                    """
                }
            )
            
            if 'result' in result and 'value' in result['result']:
                return result['result']['value']
            return []
            
        except Exception as e:
            logger.error(f"Failed to navigate and extract from {url}: {e}")
            raise

    async def close(self):
        """Close all sessions and cleanup."""
        for session_id in list(self._sessions.keys()):
            await self.close_session(session_id)
        await self.client.aclose() 