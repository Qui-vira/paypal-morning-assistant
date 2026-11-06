# Morning Assistant

An AI morning planner that also gets you paid.

You type one line, like *"Plan my morning. I have 20 minutes before my first meeting."* Claude reads your tasks, your
calendar and the clients who owe you money, and builds a timed plan that fits the time you have. If an overdue client
fits in the window, the plan includes it, and one click sends that client a real PayPal invoice.

Built for the [PayPal AI Hackathon](https://paypalaihackathon.devpost.com/).

## Try it now (for judges)

**Live demo: https://morning-assistant-production.up.railway.app**

No account or keys needed. The demo is already connected to Claude and to a PayPal **sandbox** business account.

1. Open the link. The sample morning (tasks, calendar, clients who owe) is loaded.
2. Keep the request *"Plan my morning. I have 20 minutes before my first meeting."* (or type your own) and press **Plan**.
   Claude returns a timed plan within about 20 seconds.
3. If the plan includes an invoice step, press **Send PayPal invoice**. The app creates, sends and reads back a real
   PayPal sandbox invoice (test money only) and shows its number, status (`SENT`) and the PayPal invoice link.

The hosted demo allows 40 plan or invoice calls per visitor per hour, and it does not save changes to the sample data.
To run it with your own keys, see **Run it** below.

## What it does

- **Plans the morning with AI.** Claude (Anthropic) gets the request, the task list, today's calendar and the unpaid
  clients, and returns a structured plan: start time, minutes and the reason for each step, plus what moves to later.
- **Invoices with PayPal.** The plan picks the client to invoice. The app creates the invoice, sends it, and reads it
  back through the PayPal Invoicing API (v2), so the result on screen is what PayPal actually holds.
- **Never fakes a result.** If Claude or PayPal returns an error, the app shows that error instead of a success screen.

## How it uses PayPal and AI

| Part | Tool | What it does |
|---|---|---|
| Planning | Claude (Anthropic API, structured output) | Turns a plain-English request plus tasks, calendar and debts into a timed plan, and chooses which client to invoice |
| Payments | PayPal Invoicing API v2 (sandbox) | OAuth client-credentials token, create invoice, send invoice, read it back |

The AI and the payment are one flow: the AI decides that an overdue invoice fits the next 20 minutes, and PayPal sends it.

## Run it

Requires Python 3.10+.

```bash
git clone https://github.com/Qui-vira/paypal-morning-assistant
cd paypal-morning-assistant
pip install -r requirements.txt
```

1. Set your Anthropic key: `ANTHROPIC_API_KEY=...` in your environment, or in a `.env` file next to `app.py`.
2. Copy `settings.example.json` to `settings.json` and fill in your **PayPal sandbox** app Client ID and Secret
   (developer.paypal.com > Apps & Credentials > Sandbox) and the email of a sandbox personal test account.
3. Start it:

```bash
python app.py
```

4. Open http://localhost:8615, type your request, press **Plan**, then **Send PayPal invoice**.

On a host, set `PORT`, `ANTHROPIC_API_KEY`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` and
`SANDBOX_CUSTOMER_EMAIL` as environment variables instead of `settings.json` (`Procfile` runs `python app.py`).

Your tasks, calendar and clients live in `data.json`. Edit it to try your own morning.

## Sandbox only

The app talks only to `api-m.sandbox.paypal.com`. Invoices are test money. Never put live keys in `settings.json`.

## Licence

MIT, see `LICENSE`.
