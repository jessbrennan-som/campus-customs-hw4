# Campus Customs (HW4)

Student merch website for Yale: a React + Vite + TypeScript front end and a FastAPI back end that serves the products and their photos from `data/campus_customs.db`.

## Set it up and run it

The database and the product photos are **not in this repository** (and neither is the `.env` file with the AI key). You add them after cloning.

**1. Clone and add the data pack**

```bash
git clone <this repository's URL>
cd <the cloned folder>
unzip /path/to/data.zip -d .      # the instructor's data pack: creates data/campus_customs.db and data/products/
```

After this, `data/` must contain `campus_customs.db` and a `products/` folder of photos (`data/README.md` shows the layout).

**2. Add the AI key** (only the chatbot needs it)

```bash
cp .env.example .env              # then open .env and replace the placeholder with your real PORTKEY_API_KEY
```

The API finds a `.env` in this folder, in `backend/`, or in any folder above them. Never commit `.env`.

**3. Start the back end (terminal 1, API on port 8000)**

```bash
cd backend
python3 -m venv .venv                          # first time only
.venv/bin/pip install -r requirements.txt      # first time only
.venv/bin/uvicorn main:app --reload --port 8000
```

**4. Start the front end (terminal 2, website on port 5173)**

```bash
cd frontend
npm install                                    # first time only
npm run dev
```

Open http://localhost:5173. API docs: http://localhost:8000/docs. Without the data pack the API can't start (it has no products), and without the key the chat says the assistant isn't set up yet.

Optional: `cd backend && .venv/bin/pip install -r requirements-images.txt && .venv/bin/python whiten_images.py` makes white-background copies of the photos (see "Product photos" below). Tests: `cd backend && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/pytest -q`.

## How the agent is built: four files

The chatbot is a PydanticAI agent, and its whole definition lives in four files in `backend/`:

| File | What it is |
| --- | --- |
| `prompt/prompt.md` | the instructions: personality, job, safety and conduct rules (read again on every message) |
| `agent.py` | builds the agent: the model, the instructions, the tools, the checks on its answers, the loop limit and the audit trail |
| `tools.py` | the abilities it can use (13 tools) |
| `models.py` | the checked shapes of everything it takes in and gives back |

`main.py` serves it over `POST /api/chat`. The tools read the shop's data through small helper modules (`catalogue.py`, `memory.py`, `trivia.py`, `lessons.py`, `pages.py`, `audit.py`), but those only supply facts; the agent's behavior is set by the four files above.

## API

| Route | What it returns |
| --- | --- |
| `GET /api/products` | all products (`?search=` and `?garment_type=` filter them) |
| `GET /api/products/{id}` | one product with its stock by size |
| `GET /api/products/{id}/similar` | 3 products matching its style, color or size (`?size=M` favors that size) |
| `GET /api/garment-types` | styles and how many products each has |
| `GET /api/products?category=hoodies&collection=berkeley` | the same list filtered by the Products page menus |
| `GET /api/browse-filters` | the options for those menus (categories, and "shop for" groups) with counts |
| `POST /api/gift-cards/buy`, `/check`, `/quote` | buy a gift certificate; check a code's balance; price a cart with 10% off |
| `POST /api/checkout/gift-card` | a logged-in customer pays for their cart with a gift certificate |
| `POST /api/chat/idle` | the chat has been quiet for a minute: Handsome Dan offers Yale trivia |
| `GET/POST /api/admin/lessons` | admins review what the chatbot learned from mistakes |
| `GET /images/{file}` | the product photo named in the database |

## The shop chatbot (Handsome Dan)

The chat panel in the corner of the site talks to a **PydanticAI agent** behind FastAPI. `POST /api/chat` takes a message from the website and returns the agent's reply plus, in `results`, the product cards the website shows **on the page the customer is looking at** (photo, name, price and a short description; each card opens the product's full page).

| File | Job |
| --- | --- |
| `backend/main.py` | the FastAPI app: the shop routes, the accounts routes, and `POST /api/chat` and `GET /api/chat/history` |
| `backend/agent.py` | builds the agent and wires it together: the model, the instructions, the tools, the answer shape, and two checks on its answers |
| `backend/prompt/prompt.md` | the agent's instructions (its personality, the size rule, the account and security rules) |
| `backend/tools.py` | what the agent can look up: `search_products`, `get_product`, `check_size`, `suggest_similar`, `list_styles`, `about_me`, `my_purchases`, `record_feedback`, `about_this_page`, `account_help`, `start_trivia`, `answer_trivia`, `learn_from_mistake` |
| `backend/models.py` | the Pydantic types for products, chat messages, the agent's answer (`AgentReply`) and every tool result |
| `backend/catalogue.py` | reads products and stock, so the website and the chatbot always see the same facts |
| `backend/memory.py` | what the shop remembers about a logged-in customer: purchases, the "how did it work out?" question, and the feedback they give |
| `backend/pages.py` | checks which page the website says the customer is on, so the chatbot can answer questions about it |
| `backend/admin.py`, `backend/feedback_report.py` | the compiled customer feedback, for the shop's admins |

- **Products and accounts.** The agent answers product, price, color and stock questions with live data from its tools, never from memory. For "do you have it in size X?" it follows the size rule: if a size is sold out or not made (3XL), it offers both the nearest size up and the nearest size down that are in stock. For account questions it can tell the customer who they are (only themselves, never anyone else) and how to create an account, log in, reset or change a password, but it can't see or change any password.
- **Memory.** The chatbot knows who it is talking to: a logged-in customer's own name and email (a guest has none), and it can see what they bought, only to recommend well. A logged-in customer's chat is saved in the `chat_messages` table and comes back when they log in (`POST /api/chat/resume`); a guest's chat is remembered only for the visit and never saved. If a customer bought something a few days ago, the chatbot opens by asking how it worked out and files the answer in the `customer_feedback` table. Admins read it with `python feedback_report.py` (writes `output/customer_feedback.md`) or the `/api/admin/feedback` routes, which only work for the emails listed in the `ADMIN_EMAILS` setting.
- **The page the customer is on.** Every chat message includes the page (and the size chosen on a product page). The API checks it against the database, and the chatbot can look up that page's live details, so "is this in stock in my size?" works.
- **Demo purchases.** There is no checkout yet, so `python seed_demo_purchases.py you@example.com` adds two made-up purchases to one account for trying the follow-up (`--undo` removes them).
- **Checked answers.** Pydantic forces every answer into the same shape, and a second check sends the answer back for another try if it names a product that doesn't exist.
- **Safety.** No tool can read passwords, sessions or other customers. A message the AI service's own safety filter refuses gets a polite reply and is not saved. Each person is limited to 30 messages per 15 minutes.
- **Editing the instructions:** `backend/prompt/prompt.md` is read again for every message, so changes to it apply to the very next chat, with no restart.
- **The AI model** is `gpt-5.6-luna` through Portkey. The key (`PORTKEY_API_KEY`) is read from the class-wide `.env` file, never from the code. Change the model with `SHOP_MODEL`. With no key, the chat says the assistant isn't set up yet.
- **Tests** use PydanticAI's fake models, so they cost nothing and never call the real service: `cd backend && .venv/bin/pytest -q` (125 tests).

## Audit trail and safety rules (Problem 12)

- **`output/audit_trail.json`** is an append-only record of the agent loop (`backend/audit.py`): for every chat message, the time, each tool called with short arguments and results, any retry, and the stop reason. It is one valid JSON list that new entries are added to the end of, so it is never wiped between runs. It stores no customer messages, names or emails.
- **Safety rules** are in `backend/prompt/prompt.md` ("Conduct and safety rules") and summarized with the code-enforced ones in `output/harness.md`.
- `output/harness.md` is the full guide for graders: how it works, the data types and why, all 13 tools, the safety rules, the limits and how to run everything.

## Gift certificates, trivia and learning (Problem 9)

See `output/usability.md` for every shopper-facing improvement and how it was checked.

- **Products menus:** `catalogue.py` holds the categories (Hoodies, T-shirts...) and the "shop for" groups (colleges, schools, sports, family, Yale spirit); the Products page keeps the choices in the web address.
- **Gift certificates** (`backend/giftcards.py`): buy one for a student, who enters the code in the cart and pays with it for 10% off everything. **No payment is taken and no card details are collected** (class project; the site says so). Codes are shown once and emailed (to `backend/outbox/` when no email server is set); only a fingerprint of each code is stored. Paying needs a login so the purchase is saved on the account. A banner above the header promotes the offer.
- **Yale trivia** (`backend/trivia.py`): after a quiet minute the website calls `POST /api/chat/idle` and Handsome Dan offers a 3-question multiple-choice game. The questions live in a checked list in the code; the agent must read them out exactly and the code judges the answers (tools `start_trivia`, `answer_trivia`).
- **Learning from mistakes** (`backend/lessons.py`): when a shopper says results were the wrong kind of thing, the agent corrects the search and saves a lesson with `learn_from_mistake` (a word, the wrong garment types, the closest real ones). A lesson applies to everyone after **two different customers** report it or an admin approves it; `search_products` then leaves out the wrong styles and puts the closest first. This is saved lessons, not retraining the AI.

## Accounts

Customers can create an account, log in, and reset a forgotten password. New accounts are rows in the `users` table (`first_name`, `last_name`, `email`, `password_hash`).

- **Passwords are never saved.** Each one is turned into a salted, slow hash (PBKDF2-SHA256, 600,000 rounds, a random salt per person) like `pbkdf2_sha256$600000$<salt>$<hash>`. The same password gets a different hash for every person, and a hash can't be turned back into the password.
- **Password rules:** 10 to 64 characters with a lowercase letter, an uppercase letter, a number and a symbol; nothing easy to guess (like "password" or "123456"); no part of your name or email. The sign-up page ticks them off as you type, and the server checks them again. The password has to be typed twice and match.
- **Logging in** needs only an email and password (email capitals don't matter). A wrong guess never says whether the email exists, and five wrong tries lock that email for 15 minutes.
- **Staying logged in:** a random code in an HttpOnly cookie (JavaScript can't read it). The database keeps only a fingerprint of it, in the `sessions` table.
- **My Account:** once logged in, a **My Account** button in the header opens a page with your name and email and a form to change your password. It asks for your current password first, applies the same rules to the new one, logs out every other device, and emails you a heads-up that it changed.
- **Forgot password:** enter your email and we send a link that works once, for 30 minutes. The database keeps only a fingerprint of it (`password_resets` table). Using it ends all other logins.
- **Email:** with no email server set up (the default), each email is saved as a text file in `backend/outbox/`. Open it to use the link. To send real email, set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` and `SMTP_FROM` in a `.env` file (never in the code).
- The three customers that came with the database use an older hash format (no round count written down). They can still log in: the first time they do, the API checks the usual settings and then rewrites their hash in the new format. If an old password doesn't work, "Forgot your password?" sets a new one.

Run the tests (they use a throwaway copy of the database):

```bash
cd backend
.venv/bin/pip install -r requirements-dev.txt   # first time only
.venv/bin/pytest -q
```

## Product photos

Many of the original photos in `data/products/` have a black background. `backend/whiten_images.py` paints those backgrounds white and saves the results in `data/products-white/`, and the API serves those first (it falls back to the original). The originals are never changed. To redo it:

```bash
cd backend
.venv/bin/pip install -r requirements-images.txt   # first time only
.venv/bin/python whiten_images.py
```

Campus photos in `frontend/public/campus/` come from Wikimedia Commons (credits are in the site footer).
