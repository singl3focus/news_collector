import secrets
import json
from typing import Tuple, Optional

KEY_ID = "id"
KEY_USERNAME = "username"
KEY_TOCKENS = "tokens"

def create_user(username: str, redis_client) -> dict:
    user_id = f"user_{secrets.token_hex(8)}"
    token = secrets.token_urlsafe(32)
    
    user_data = {
        KEY_ID: user_id,
        KEY_USERNAME: username,
        KEY_TOCKENS: [token]
    }
    
    # Сохраняем в Redis
    redis_client.set(f"user:{user_id}", json.dumps(user_data))
    redis_client.set(f"auth:token:{token}", user_id)
    redis_client.sadd(f"user:channels:{user_id}", 0)  # Дефолтная подписка
    
    return {"user_id": user_id, "token": token}

def authenticate(username: str, redis_client) -> Tuple[bool, Optional[str]]:
    for key in redis_client.scan_iter("user:*"):
        user = json.loads(redis_client.get(key))
        if user[KEY_USERNAME] == username:
            token = secrets.token_urlsafe(32)
            user[KEY_TOCKENS].append(token)
            redis_client.set(key, json.dumps(user))
            redis_client.set(f"auth:token:{token}", user["id"])
            return token
    return None
