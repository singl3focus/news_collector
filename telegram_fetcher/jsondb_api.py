from fastapi import FastAPI
from pydantic import BaseModel
from jsondb import JsonDB

db = JsonDB()

class ChannelIn(BaseModel):
    link: str
    title: str = ""

app = FastAPI()

@app.get("/channels")
def get_channels():
    return db.get_channels()

@app.post("/channels")
def add_channel(channel: ChannelIn):
    db.add_channel(channel.dict())
    return {"ok": True}

@app.delete("/channels/{link}")
def delete_channel(link: str):
    db.remove_channel(link)
    return {"ok": True} 