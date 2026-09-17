import asyncio
import base64
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import websockets
from PIL import Image

ROOT = Path(r"D:\AWS_Udacity\project_assignment_02")
panel_path = ROOT / "evidence/panels/03_rag.html"
target_img = ROOT / "evidence/screenshots/03_rag.jpg"

async def capture():
    # Use Chrome on port 9222
    uri = "ws://127.0.0.1:9222/devtools/page/70DD1640848C53AB92FEBB23CEDF10DF"
    async with websockets.connect(uri) as ws:
        # Navigate to panel
        print("Navigating to", panel_path.as_uri())
        await ws.send(json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": panel_path.as_uri()}}))
        await ws.recv()
        await asyncio.sleep(2)
        
        # Get bounding rect of #outcome-panel
        expr = """
        (() => {
            const el = document.querySelector('#outcome-panel');
            const rect = el.getBoundingClientRect();
            return {
                x: rect.x + window.scrollX,
                y: rect.y + window.scrollY,
                width: rect.width,
                height: rect.height
            };
        })()
        """
        await ws.send(json.dumps({"id": 2, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True}}))
        rect = json.loads(await ws.recv())["result"]["result"]["value"]
        print("Bounding rect:", rect)
        
        # Capture screenshot with clip
        clip = {
            "x": rect["x"],
            "y": rect["y"],
            "width": rect["width"],
            "height": rect["height"],
            "scale": 1
        }
        await ws.send(json.dumps({
            "id": 3,
            "method": "Page.captureScreenshot",
            "params": {"format": "jpeg", "quality": 90, "clip": clip}
        }))
        resp = json.loads(await ws.recv())
        b64data = resp["result"]["data"]
        raw_bytes = base64.b64decode(b64data)
        target_img.write_bytes(raw_bytes)
        print(f"Saved {len(raw_bytes)} bytes to {target_img.name}")

if __name__ == "__main__":
    asyncio.run(capture())
    
    img = Image.open(target_img)
    w, h = img.size
    digest = hashlib.sha256(target_img.read_bytes()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    print(f"Captured 03_rag.jpg: {w}x{h}, SHA-256: {digest}")

    manifest_path = ROOT / "evidence/screenshots/CAPTURE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    for p in manifest["panels"]:
        if p["file"] == "03_rag.jpg":
            p["width"] = w
            p["height"] = h
            p["sha256"] = digest
            p["source"] = "Local rendering of passing September 17 AWS Knowledge Base runtime output"
            p["captured_utc"] = now

    manifest["checked_utc"] = now
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Updated CAPTURE_MANIFEST.json successfully!")
