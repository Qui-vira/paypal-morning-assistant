"""Morning Assistant (Day 15). A small, real app: Claude plans the morning from the task list and calendar,
and the app sends a real PayPal sandbox invoice (test money) to a client who owes.

Run:   pip install -r requirements.txt && python app.py        then open http://localhost:8615
Keys:  ANTHROPIC_API_KEY from the environment or a .env file next to app.py.
       PayPal sandbox keys go in settings.json (copy settings.example.json). Sandbox only, never live keys.
"""
import base64, json, os, urllib.error, urllib.parse, urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List

import anthropic
from pydantic import BaseModel

HERE = Path(__file__).parent
VAULT_ENV = HERE / ".env"
PORT = int(os.environ.get("PORT", 8615))
HOSTED = bool(os.environ.get("PORT"))     # set by the host (Railway): public judge demo
PAYPAL = "https://api-m.sandbox.paypal.com"  # sandbox only, on purpose
MODEL = "claude-opus-5-5"


def env_key(name):
    if os.environ.get(name):
        return os.environ[name]
    if not VAULT_ENV.exists():
        return None
    for line in VAULT_ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def load(name, default=None):
    p = HERE / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


# ---------- Claude: the morning plan ----------

class Step(BaseModel):
    start: str          # "08:52"
    minutes: int
    task: str
    why: str


class Plan(BaseModel):
    summary: str        # one short line
    steps: List[Step]
    later: List[str]    # tasks moved out of this window, each with a few words of reason
    invoice_client_id: str  # the client from clients_who_owe to invoice now, or "" if none


SYSTEM = (
    "You are a morning assistant for a busy creator. You get a task list, a calendar and a list of clients "
    "who owe money, plus a request in plain words. Build a realistic plan that fits the time the request gives. "
    "Put quick, high-value and overdue items first. Anything that cannot fit goes in 'later'. "
    "If a client owes money and invoicing fits, include a step to send that invoice and set invoice_client_id. "
    "The app itself sends invoices through PayPal in one click, so an invoice step is quick and never needs an "
    "address looked up. Write short, plain English. Times are 24-hour HH:MM."
)

claude = anthropic.Anthropic(api_key=env_key("ANTHROPIC_API_KEY"))


def make_plan(request_text, now):
    data = load("data.json")
    prompt = (f"Now: {now}\nRequest: {request_text}\n\n"
              f"Tasks: {json.dumps(data['tasks'])}\nCalendar today: {json.dumps(data['calendar'])}\n"
              f"Clients who owe: {json.dumps(data['clients_who_owe'])}")
    resp = claude.messages.parse(model=MODEL, max_tokens=4000, system=SYSTEM,
                                 messages=[{"role": "user", "content": prompt}], output_format=Plan)
    if resp.stop_reason == "refusal":
        raise RuntimeError("Claude declined this request.")
    return resp.parsed_output.model_dump()


# ---------- PayPal sandbox invoice ----------

def paypal(method, path, token=None, body=None, basic=None, form=None):
    headers = {"Accept": "application/json"}
    data = None
    if basic:
        headers["Authorization"] = "Basic " + base64.b64encode(basic.encode()).decode()
    if token:
        headers["Authorization"] = "Bearer " + token
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(PAYPAL + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise RuntimeError(f"PayPal said {e.code}: {detail}")


def paypal_settings():
    """PayPal sandbox keys: environment variables on the hosted demo, settings.json when run locally."""
    if os.environ.get("PAYPAL_CLIENT_ID"):
        return {"paypal_client_id": os.environ["PAYPAL_CLIENT_ID"], "paypal_client_secret": os.environ["PAYPAL_CLIENT_SECRET"],
                "sandbox_customer_email": os.environ["SANDBOX_CUSTOMER_EMAIL"], "invoicer_name": os.environ.get("INVOICER_NAME", "Big Quiv")}
    return load("settings.json")


def send_invoice(client_id):
    s = paypal_settings()
    if not s or not s.get("paypal_client_id") or "your sandbox" in s.get("paypal_client_id", ""):
        raise RuntimeError("Add your PayPal sandbox keys to settings.json first (copy settings.example.json).")
    client = next(c for c in load("data.json")["clients_who_owe"] if c["id"] == client_id)
    email = s["sandbox_customer_email"]  # sandbox test buyer, never a real client
    token = paypal("POST", "/v1/oauth2/token", basic=f"{s['paypal_client_id']}:{s['paypal_client_secret']}",
                   form={"grant_type": "client_credentials"})["access_token"]
    created = paypal("POST", "/v2/invoicing/invoices", token, {
        "detail": {"currency_code": client["currency"], "note": f"Thanks, {client['name']}. Test invoice (PayPal sandbox)."},
        "invoicer": {"name": {"given_name": s.get("invoicer_name", "Big Quiv")}},
        "primary_recipients": [{"billing_info": {"email_address": email}}],
        "items": [{"name": client["item"], "quantity": "1",
                   "unit_amount": {"currency_code": client["currency"], "value": client["amount"]}}],
    })
    inv_id = created.get("id") or created["href"].rstrip("/").split("/")[-1]
    paypal("POST", f"/v2/invoicing/invoices/{inv_id}/send", token, {"send_to_recipient": True, "send_to_invoicer": True})
    inv = paypal("GET", f"/v2/invoicing/invoices/{inv_id}", token)
    out = {"id": inv_id, "number": inv.get("detail", {}).get("invoice_number"), "status": inv.get("status"),
           "client": client["name"], "item": client["item"], "amount": client["amount"], "currency": client["currency"],
           "to": email, "link": inv.get("detail", {}).get("metadata", {}).get("recipient_view_url"),
           "sandbox": True, "at": datetime.now().isoformat(timespec="seconds")}
    if not HOSTED:
        log = load("invoices.log.json", [])
        log.append(out)
        (HERE / "invoices.log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    return out


# ---------- web server ----------

_hits = {}


def allow(h, per_hour=40):
    """Hosted demo only: at most 40 plan/invoice calls per visitor per hour, so the public demo cannot be drained."""
    ip = (h.headers.get("X-Forwarded-For") or h.client_address[0]).split(",")[0].strip()
    now = datetime.now().timestamp(); recent = [t for t in _hits.get(ip, []) if now - t < 3600]
    if len(recent) >= per_hour:
        _hits[ip] = recent; return False
    recent.append(now); _hits[ip] = recent; return True


class Handler(BaseHTTPRequestHandler):
    def send(self, code, obj, ctype="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self.send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/data":
            return self.send(200, load("data.json"))
        self.send(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        try:
            if HOSTED and self.path in ("/api/plan", "/api/invoice") and not allow(self):
                return self.send(429, {"error": "Demo limit reached for this hour. Please try again later."})
            if self.path == "/api/plan":
                return self.send(200, make_plan(body["request"], body.get("now") or datetime.now().strftime("%H:%M")))
            if self.path == "/api/invoice":
                return self.send(200, send_invoice(body["client_id"]))
            if self.path == "/api/data":
                if HOSTED:   # the public demo keeps the sample morning; edits stay in the visitor's browser
                    return self.send(200, {"ok": True, "saved": False})
                (HERE / "data.json").write_text(json.dumps(body, indent=2), encoding="utf-8")
                return self.send(200, {"ok": True})
            self.send(404, {"error": "not found"})
        except Exception as e:  # shown in the app, so a failure is never faked as success
            self.send(500, {"error": str(e)})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    host = "0.0.0.0" if HOSTED else "127.0.0.1"
    print(f"Morning Assistant on http://{host}:{PORT}")
    ThreadingHTTPServer((host, PORT), Handler).serve_forever()
