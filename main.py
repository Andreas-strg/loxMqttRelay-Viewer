import asyncio
import json
import secrets
from aiomqtt import Client, MqttError
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from uvicorn import Config, Server
import os

# 📡 MQTT Einstellungen
MQTT_BROKER = os.getenv("MQTT_BROKER", "")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

# ✅ OPTIONAL: Passwort für Webseite
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "")  # leer = keine Abfrage

# Windows Fix für asyncio + aiomqtt
if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# FastAPI
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
security = HTTPBasic()


def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if WEB_PASSWORD:
        valid = secrets.compare_digest(credentials.password, WEB_PASSWORD)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Basic"},
            )
    return True


@app.get("/")
async def index(auth: bool = Depends(check_auth)):
    return FileResponse("index.html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    mqtt_connected = False
    current_topic = "#"
    last_topic = "#"
    topic_event = asyncio.Event()

    async def broadcast_status():
        await websocket.send_json({"type": "status", "connected": mqtt_connected, "topic": current_topic})

    async def broadcast_message(topic: str, value: str):
        await websocket.send_json({"type": "message", "topic": topic, "value": value})

    async def broadcast_json(prefix: str, obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_prefix = f"{prefix}_{key}"
                await broadcast_json(new_prefix, value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_prefix = f"{prefix}_{i}"
                await broadcast_json(new_prefix, item)
        else:
            # True/False zu 1/0
            if isinstance(obj, bool):
                obj = int(obj)
            clean_prefix = prefix.replace(": ", ":")
            await broadcast_message(clean_prefix, str(obj))

    async def mqtt_task():
        nonlocal mqtt_connected, last_topic, current_topic
        while True:
            try:
                print("🔌 Verbinde zu MQTT Broker...")
                async with Client(
                    hostname=MQTT_BROKER, port=MQTT_PORT, username=MQTT_USERNAME, password=MQTT_PASSWORD
                ) as client:
                    mqtt_connected = True
                    print("✅ MQTT verbunden!")
                    await broadcast_status()

                    await client.subscribe(current_topic)
                    last_topic = current_topic
                    print(f"📡 Abonniert: {current_topic}")

                    async def handle_messages():
                        async for message in client.messages:
                            clean_topic = str(message.topic).replace("/", "_").replace(": ", ":")
                            if isinstance(message.payload, bytes):
                                payload = message.payload.decode("utf-8")
                            else:
                                payload = str(message.payload)
                            try:
                                data = json.loads(payload)
                                if isinstance(data, dict):
                                    await broadcast_json(clean_topic, data)
                                else:
                                    await broadcast_message(clean_topic, str(payload))
                            except json.JSONDecodeError:
                                await broadcast_message(clean_topic, str(payload))

                    async def handle_topic_changes():
                        nonlocal last_topic, current_topic
                        while True:
                            await topic_event.wait()
                            topic_event.clear()
                            if current_topic != last_topic:
                                print(f"🔄 Topic geändert → {current_topic}")
                                await client.unsubscribe(last_topic)
                                await client.subscribe(current_topic)
                                last_topic = current_topic
                                await broadcast_status()

                    await asyncio.gather(handle_messages(), handle_topic_changes())

            except MqttError as e:
                mqtt_connected = False
                await broadcast_status()
                print(f"❌ MQTT Fehler: {e}")
                await asyncio.sleep(5)

    mqtt_task_instance = asyncio.create_task(mqtt_task())

    try:
        await broadcast_status()
        while True:
            data = await websocket.receive_text()
            print(f"➡️ Neues Topic für WS: {data}")
            current_topic = data
            topic_event.set()
    except WebSocketDisconnect:
        mqtt_task_instance.cancel()
        print("❌ WS getrennt → MQTT-Task beendet.")


async def main():
    config = Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
