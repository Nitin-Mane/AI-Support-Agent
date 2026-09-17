"""Render saved runtime responses as clearly labelled evidence documents.

These files display recorded output; they do not call AWS or simulate its console.
Capture their outcome panels in Chrome to produce the accompanying screenshots.
"""

import hashlib
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "evidence/panels"
DESTINATION.mkdir(exist_ok=True)
SCENARIOS = {
    "01_order": "Test 1 | Order tracking",
    "02_refund": "Test 2 | Refund processing",
    "03_rag": "Test 3 | Knowledge Base retrieval",
    "04_memory_a": "Test 4 | Memory: first session",
    "04_memory_b": "Test 4 | Memory: new session",
    "05_discount": "Test 5 | Loyalty calculation",
    "06_browser": "Test 6 | Browser page title",
}

for name, title in SCENARIOS.items():
    source = ROOT / "evidence/live" / (name + (".txt" if name == "01_order" else ".json"))
    raw = source.read_text(encoding="utf-8")
    if name == "01_order":
        started = raw.splitlines()[0].removeprefix("Started UTC: ")
        prompt = "Can you track order ORD-001?"
        response = raw.split("Response:\n", 1)[1].split("\nSTDERR", 1)[0].strip()
        metadata = "CLI: agentcore invoke | Exit code: 0 | Customer: CUST-123 | Session: t1"
    else:
        record = json.loads(raw)
        started = record["started_utc"]
        prompt = record["input"]["prompt"]
        response = record["output"]["response"]
        metadata = (
            f"HTTP {record['http_status']} | Customer: {record['input']['customer_id']}"
            f" | Session: {record['input']['session_id']}\n"
            f"Runtime session: {record['runtime_session_id']}"
        )
    status = "Recorded successful scenario — Knowledge Base RAG verified" if name == "03_rag" else "Recorded successful scenario"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    html = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><title>{escape(title)}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 24px; background: #f3f5f8; color: #152238; font: 16px/1.5 'Segoe UI', sans-serif; }}
main {{ width: 1100px; max-width: 100%; padding: 28px 32px; background: white; border: 1px solid #d7dfe9; border-radius: 10px; }}
.eyebrow {{ font-size: 13px; color: #50637e; letter-spacing: 1px; }}
h1 {{ font-size: 26px; margin: 6px 0 12px; }}
h2 {{ font-size: 15px; margin: 16px 0 6px; }}
.status {{ color: #12614c; font-weight: 600; }}
.meta, footer {{ color: #53647a; font-size: 12px; white-space: pre-wrap; overflow-wrap: anywhere; }}
pre {{ margin: 0; padding: 15px 18px; background: #f4f7fb; border-left: 3px solid #406aa5; white-space: pre-wrap; overflow-wrap: anywhere; font: 15px/1.5 Consolas, monospace; }}
footer {{ margin-top: 20px; padding-top: 12px; border-top: 1px solid #d7dfe9; }}
</style>
<main id="outcome-panel">
<div class="eyebrow">AI SUPPORT AGENT · ASSIGNMENT 02 · RECORDED AWS OUTPUT</div>
<h1>{escape(title)}</h1>
<div class="status">{escape(status)}</div>
<p class="meta">Run started (UTC): {escape(started)}\n{escape(metadata)}</p>
<h2>Request</h2><pre>{escape(prompt)}</pre>
<h2>Agent response — verbatim</h2><pre>{escape(response)}</pre>
<footer>Source: {source.relative_to(ROOT).as_posix()}\nSHA-256: {digest}\nSaved runtime evidence, displayed locally. This is not a live AWS console view.\nThe test deployment was removed after evidence collection. Course fixtures represent no real payments.</footer>
</main></html>"""
    (DESTINATION / f"{name}.html").write_text(html, encoding="utf-8")
print(f"Created {len(SCENARIOS)} panels in {DESTINATION}")
