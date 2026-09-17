from pathlib import Path
from playwright.sync_api import sync_playwright
import hashlib
import json
from datetime import datetime, timezone
from PIL import Image

ROOT = Path(r"D:\AWS_Udacity\project_assignment_02")
panel_path = ROOT / "evidence/panels/03_rag.html"
target_img = ROOT / "evidence/screenshots/03_rag.jpg"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(panel_path.as_uri())
    page.wait_for_selector("#outcome-panel")
    panel = page.locator("#outcome-panel")
    panel.screenshot(path=str(target_img), type="jpeg", quality=90)
    browser.close()

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
