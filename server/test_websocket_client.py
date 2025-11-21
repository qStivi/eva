"""
Simple WebSocket client for testing the conversation endpoint.

Usage:
    python test_websocket_client.py
"""

import asyncio
import json
import websockets
from app.config import settings


async def test_websocket():
    """Test WebSocket conversation endpoint."""
    uri = f"ws://localhost:8080/ws/conversation?token={settings.secret_key}"

    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as websocket:
        print("Connected!")

        # Receive welcome message
        welcome = await websocket.recv()
        print(f"\n[SERVER] {welcome}\n")
        welcome_data = json.loads(welcome)

        if welcome_data.get("type") == "system" and welcome_data.get("event") == "connected":
            print("[OK] Welcome message received")
            print(f"  Conversation ID: {welcome_data['data']['conversation_id']}")
            print(f"  Character: {welcome_data['data']['character_name']}")
            print(f"  User: {welcome_data['data']['display_name']}")

        # Send test message
        test_message = {
            "type": "message",
            "content": "Hello Eva! Can you hear me?",
            "metadata": {
                "test": True
            }
        }

        print(f"\n[SENDING] {test_message['content']}")
        await websocket.send(json.dumps(test_message))

        # Receive response chunks
        print("\n[EVA] ", end="", flush=True)
        full_response = ""
        chunk_count = 0

        while True:
            chunk_data = await websocket.recv()
            chunk = json.loads(chunk_data)

            if chunk.get("type") == "system":
                print(f"\n[SYSTEM] {chunk.get('event')}: {chunk.get('data', {}).get('status', '')}")
                print("[EVA] ", end="", flush=True)
                continue

            if chunk.get("type") == "response_chunk":
                content = chunk.get("content", "")
                done = chunk.get("done", False)

                if content:
                    print(content, end="", flush=True)
                    full_response += content
                    chunk_count += 1

                if done:
                    metadata = chunk.get("metadata", {})
                    print(f"\n\n[OK] Response complete")
                    print(f"  Chunks: {chunk_count}")
                    print(f"  Total chunks: {metadata.get('total_chunks', 'N/A')}")
                    print(f"  Generation time: {metadata.get('generation_time_ms', 'N/A')}ms")
                    break

            elif chunk.get("type") == "error":
                print(f"\n\n[ERROR] {chunk.get('message')}")
                print(f"  Code: {chunk.get('code')}")
                print(f"  Recoverable: {chunk.get('recoverable')}")
                break

        print(f"\n\nFull response ({len(full_response)} chars):")
        print(f'"{full_response}"')

        print("\n[OK] WebSocket test complete!")


if __name__ == "__main__":
    asyncio.run(test_websocket())
