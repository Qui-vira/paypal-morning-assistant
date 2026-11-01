"""Record the hackathon demo video of the real app (Playwright screen capture of http://localhost:8615).

Runs the real flow at a human pace: the data, the request typed in, Claude's plan arriving, the PayPal sandbox invoice
sent and read back. Writes demo/raw/*.webm. Usage: start `python app.py` first, then `python demo/record_demo.py`.
"""
import os, time, urllib.request
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw"); os.makedirs(OUT, exist_ok=True)
for _ in range(30):
    try: urllib.request.urlopen("http://localhost:8615/api/data", timeout=2); break
    except Exception: time.sleep(1)
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    ctx = b.new_context(viewport={"width": 1920, "height": 1080}, record_video_dir=OUT, record_video_size={"width": 1920, "height": 1080})
    pg = ctx.new_page()
    pg.goto("http://localhost:8615", wait_until="networkidle"); pg.wait_for_timeout(4000)   # tasks, calendar, unpaid client
    pg.click("#req"); pg.keyboard.type("Plan my morning. I have 20 minutes before my first meeting.", delay=70)
    pg.wait_for_timeout(1200); pg.click("#go")
    pg.wait_for_function("document.querySelector('#plan').innerText.length > 40", timeout=180000)
    pg.wait_for_timeout(7000)                                                                  # read the plan
    pg.click("#send")
    pg.wait_for_function("!document.querySelector('#invoice').innerText.includes('Sending') && document.querySelector('#invoice').innerText.length > 30", timeout=180000)
    pg.wait_for_timeout(7000)                                                                  # invoice sent + toast
    ctx.close(); b.close()
print("recorded:", os.listdir(OUT))
