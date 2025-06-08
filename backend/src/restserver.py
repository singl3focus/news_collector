from fastapi import FastAPI
import uvicorn
import redis
from typing import Optional

# Фабрика для создания приложения
def create_app(redis_host: str = "localhost", redis_port: int = 6379) -> FastAPI:
    # Создаем клиент Redis с переданными параметрами
    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        decode_responses=True
    )
    
    # Инициализируем сервис
    redis_service = RedisService(redis_client)
    
    app = FastAPI()
    api_key_scheme = APIKeyHeader(name="Authorization")
    
    # Генерируем зависимости
    get_current_user = redis_service.get_current_user_dependency()
    
    # Регистрируем эндпоинты
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
