import asyncio
import websockets

async def test():
    print("Testing connection...")
    try:
        async with websockets.connect("wss://katanori-backend.tobira-sys.workers.dev") as ws:
            print("Success")
    except Exception as e:
        print("Error:", e)

asyncio.run(test())
