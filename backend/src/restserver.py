from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import APIKeyHeader
import redis
import secrets
import json
from typing import Optional, Dict, List

KEY_ID = "id"
KEY_USERNAME = "username"
KEY_TOKENS = "tokens"

class RedisService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

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

def create_app(redis_host: str = "localhost", redis_port: int = 6379):
    app = FastAPI()
    
    # Создаем схему аутентификации
    api_key_scheme = APIKeyHeader(name="Authorization")
    
    # Инициализация Redis
    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        decode_responses=True
    )
    redis_service = RedisService(redis_client)
    
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

    @app.post("/users/{user_id}/channels")
    def add_channel(channel_id: int, user_id: str = Depends(get_current_user)):
        redis_service.add_channel(user_id, channel_id)
        return {"status": "added", "channel_id": channel_id}

    @app.delete("/users/{user_id}/channels/{channel_id}")
    def remove_channel(channel_id: int, user_id: str = Depends(get_current_user)):
        redis_service.remove_channel(user_id, channel_id)
        return {"status": "removed", "channel_id": channel_id}

    return app
