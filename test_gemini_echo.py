import asyncio
import websockets
import json

async def test_echo():
    print("Connecting to DO...")
    try:
        async with websockets.connect("wss://katanori-backend.tobira-sys.workers.dev") as ws:
            print("Connected! Waiting for setupComplete...")
            # 5秒間受信を待つ
            for _ in range(5):
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    print(f"Received: {message[:100]}...")
                except asyncio.TimeoutError:
                    print("Waiting...")
                    
            print("Sending dummy text...")
            payload = {
                "clientContent": {
                    "turns": [{"role": "user", "parts": [{"text": "こんにちは"}]}],
                    "turnComplete": True
                }
            }
            await ws.send(json.dumps(payload))
            
            # 返答を待つ
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print(f"Received: {message[:100]}...")
                
    except Exception as e:
        print("Error:", e)

asyncio.run(test_echo())
