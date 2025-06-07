from fastapi import FastAPI, WebSocket

app = FastAPI()
queue = None  # будет подставлен из main.py

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        msg = await queue.get()
        await websocket.send_json(msg) 