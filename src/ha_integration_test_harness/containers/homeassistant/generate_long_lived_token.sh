#!/usr/bin/env bash
set -e

# Generate a long-lived access token using Home Assistant's websocket API
# Usage: generate_long_lived_token.sh <short_lived_token>

SHORT_LIVED_TOKEN="$1"

if [ -z "$SHORT_LIVED_TOKEN" ]; then
  echo "❌ Error: No token provided"
  echo "Usage: $0 <short_lived_token>"
  exit 1
fi

echo "🔑 Generating long-lived access token via websocket..."

# Use Python with the third-party `websockets` library to talk to Home Assistant's websocket API.
# Note: The `websockets` package must be installed and available in this environment for the script to work.
# The here-doc delimiter is single-quoted to prevent shell variable expansion inside the Python script.
python3 - "$SHORT_LIVED_TOKEN" <<'PYTHON_SCRIPT'
import asyncio
import json
import sys
import websockets

async def generate_long_lived_token(token):
    uri = "ws://localhost:8123/api/websocket"
    
    try:
        # Connect to the websocket with a longer timeout
        websocket = await asyncio.wait_for(
            websockets.connect(uri, ping_interval=None, close_timeout=10),
            timeout=10
        )
        
        try:
            # 1. Receive auth_required message
            auth_required = await asyncio.wait_for(websocket.recv(), timeout=5)
            auth_msg = json.loads(auth_required)
            
            if auth_msg.get("type") != "auth_required":
                print(f"❌ Unexpected message: {auth_msg}", file=sys.stderr)
                sys.exit(1)
            
            # 2. Send auth message with short-lived token
            await websocket.send(json.dumps({
                "type": "auth",
                "access_token": token
            }))
            
            # 3. Receive auth_ok message
            auth_response = await asyncio.wait_for(websocket.recv(), timeout=5)
            auth_result = json.loads(auth_response)
            
            if auth_result.get("type") != "auth_ok":
                print(f"❌ Authentication failed: {auth_result}", file=sys.stderr)
                sys.exit(1)
            
            # 4. Request long-lived access token
            await websocket.send(json.dumps({
                "id": 1,
                "type": "auth/long_lived_access_token",
                "client_name": "Integration Tests",
                "client_icon": "N/A",
                "lifespan": 3650  # 10 years in days - effectively permanent for testing
            }))
            
            # 5. Receive the long-lived token
            token_response = await asyncio.wait_for(websocket.recv(), timeout=5)
            token_result = json.loads(token_response)
            
            if not token_result.get("success"):
                print(f"❌ Failed to create long-lived token: {token_result}", file=sys.stderr)
                sys.exit(1)
            
            # 6. Write the long-lived token to the shared data directory
            long_lived_token = token_result["result"]
            with open("/shared_data/.ha_token", "w") as f:
                f.write(long_lived_token)

        finally:
            # Properly close the websocket connection
            await websocket.close()
            
    except asyncio.TimeoutError:
        print(f"❌ Timeout waiting for websocket response", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error generating long-lived token: {e}", file=sys.stderr)
        sys.exit(1)

# Run the async function
asyncio.run(generate_long_lived_token(sys.argv[1]))
PYTHON_SCRIPT

if [ $? -ne 0 ] || [ ! -f /shared_data/.ha_token ]; then
  echo "❌ Failed to generate long-lived access token"
  exit 1
fi

echo "✅ Long-lived access token generated and saved to /shared_data/.ha_token"
