from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.security import APIKeyHeader
import redis
import secrets
import json
import requests
import logging
from typing import Optional, Dict, List
from .ranking.analysis_stock_market import MoexStockAnalyzer

logger = logging.getLogger(__name__)

KEY_ID = "id"
KEY_USERNAME = "username"
KEY_TOKENS = "tokens"

class RedisService:
    def __init__(self, redis_client: redis.Redis, domain: str):
        self.redis = redis_client
        self.domain = domain

    def create_user(self, username: str) -> Dict[str, str]:
        user_id = f"user_{secrets.token_hex(8)}"
        token = secrets.token_urlsafe(32)
        
        user_data = {
            KEY_ID: user_id,
            KEY_USERNAME: username,
            KEY_TOKENS: [token]
        }
        
        self.redis.set(f"user:{user_id}", json.dumps(user_data))
        self.redis.set(f"auth:token:{token}", user_id)
        self.redis.sadd(f"user:channels:{user_id}", 0)
        
        return {"user_id": user_id, "token": token}

    def authenticate(self, username: str) -> Optional[str]:
        for key in self.redis.scan_iter("user:*"):
            user_data = self.redis.get(key)
            if user_data is None:
                continue
                
            user = json.loads(user_data)
            if user.get(KEY_USERNAME) == username:
                token = secrets.token_urlsafe(32)
                user[KEY_TOKENS].append(token)
                self.redis.set(key, json.dumps(user))
                self.redis.set(f"auth:token:{token}", user[KEY_ID])
                return token
        return None

    def get_current_user_dependency(self, api_key_scheme: APIKeyHeader):  # Принимаем схему как аргумент
        def _get_current_user(token: str = Depends(api_key_scheme)) -> str:
            user_id = self.redis.get(f"auth:token:{token}")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token")
            return user_id
        return _get_current_user

    def add_channel(self, user_id: str, channel_id: int):
        self.redis.sadd(f"user:channels:{user_id}", channel_id)
    
    def remove_channel(self, user_id: str, channel_id: int):
        self.redis.srem(f"user:channels:{user_id}", channel_id)

    def remove_all_channels(self, user_id: str) -> None:
        self.redis.delete(f"user:channels:{user_id}")

    def get_channel_id_by_link(self, channel_name: str) -> int:
        try:
            logger.info(f"http://{self.domain}/api/channel_id/{channel_name}")
            response = requests.get(f"http://{self.domain}/api/channel_id/{channel_name}")
            response.raise_for_status()
            
            data = response.json()
            if not data.get("ok"):
                raise HTTPException(status_code=400, detail="Invalid channel link")
                
            return data["channel_id"]
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch channel_id: {e}")
        
    def external_api_add_channel(self, link: str) -> bool:
        try:
            response = requests.post(
                "http://{self.domain}/api/add_channel",
                json={"link": link}
            )
            return response.json().get("ok", False)
        except Exception:
            return 

def create_app(domain: str, redis_host: str = "localhost", redis_port: int = 6379):
    app = FastAPI()
    
    # Создаем схему аутентификации
    api_key_scheme = APIKeyHeader(name="Authorization")
    
    # Инициализация Redis
    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        decode_responses=True
    )
    redis_service = RedisService(redis_client, domain)

    moex_stock_analyzer = MoexStockAnalyzer([])
    
    # Передаем схему аутентификации при создании зависимости
    get_current_user = redis_service.get_current_user_dependency(api_key_scheme)
    
    @app.post("/register")
    def register(username: str):
        try:
            user_data = redis_service.create_user(username)
            return {"status": "success", "token": user_data["token"]}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/login")
    def login(username: str):
        token = redis_service.authenticate(username)
        if not token:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"status": "success", "token": token}

    @app.post("/users/channels")
    def add_channel(channel_name: str, user_id: str = Depends(get_current_user)):
        link = f"https://t.me/{channel_name}"
        channel_id = redis_service.get_channel_id_by_link(channel_name)

        redis_service.add_channel(user_id, channel_id)
        redis_service.external_api_add_channel(link)
        return {"status": "added", "channel_id": channel_id}

    @app.delete("/users/channels")
    def remove_channel(channel_name: int, user_id: str = Depends(get_current_user)):
        channel_id = redis_service.get_channel_id_by_link(channel_name)

        redis_service.remove_channel(user_id, channel_id)
        return {"status": "removed", "channel_id": channel_id}

    @app.delete("/user/channels/all")
    def remove_all_channels(user_id: str = Depends(get_current_user)):
        redis_service.remove_all_channels(user_id)
        return {"status": "all channels removed"}
    
    @app.get("/graph/index")
    def get_index_graph(ticker: str, minutes_back: int = 300, interval: int = 10):
        allows = ['IMOEX', 'RTSI', 'MOEX10', 'MOEXBMI', 'RTSSTD', 'MCFTR', 'RGBITR']
        if ticker not in allows:
            raise HTTPException(status_code=404, detail="Index not available")

        try:
            # Ограничение максимальной глубины
            minutes_back = min(minutes_back, 10000)  
            
            # Корректировка интервала
            if interval not in [1, 5, 10, 15, 30, 60]:
                interval = 10

            buf = moex_stock_analyzer.plot_separate_charts(
                ticker, 
                minutes_back=minutes_back,
                interval=interval
            )
            return Response(
                content=buf.getvalue(),
                media_type="image/png",
                headers={"Content-Disposition": f"inline; filename={ticker}_chart.png"}
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Chart generation failed: {str(e)}"
            )

    return app

