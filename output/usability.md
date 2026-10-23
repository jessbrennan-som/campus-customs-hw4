# Usability improvements (beyond the homework requirements)

Everything below is something a shopper can see or feel in the running Campus Customs site. Each item says **what it does**, **why it helps the shopper**, and **where to see it**. Section 1 is the newest work (Problem 9). Sections 2 and 3 are the improvements added in earlier problems that the homework did not ask for. Section 4 says how each item was checked in the running app.

To try it: start the API and the website (see `README.md`), then open http://localhost:5173.

---

## 1. New in Problem 9

### Front end

| # | Improvement | What it does and why it helps | Where to see it |
| --- | --- | --- | --- |
| 1 | **Category dropdown** | Sorts the catalogue into the kinds of thing people search for: Hoodies, T-shirts, Long-sleeve & performance, Jackets & fleece, Quarter-zips, Crewnecks & sweatshirts. Each option shows how many products it holds, and options with nothing in them are left out, so a shopper never picks an empty shelf. | **Products** page, "Category" menu |
| 2 | **"Shop for" dropdown** | Groups products by who or what they are for: residential colleges, Yale schools, sports, family (Mom, Dad, Grandma...) and Yale spirit (Bulldogs, The Game, Boola Boola). It works with the Category menu, so "hoodies" plus "hockey" shows only hockey hoodies. This is how a parent finds "something for my daughter's college" without knowing the product names. | **Products** page, "Shop for" menu |
| 3 | **Shareable filtered pages** | The two menus are kept in the web address (`/products?category=hoodies&shop=hockey`), so the back button works and a filtered page can be bookmarked or sent to someone. | Choose a filter, then look at the address bar |
| 4 | **Gift Certificates in the main menu** | A new menu item next to Products, and a link in the footer, so gift buyers can find it from every page. | Top menu, **Gift Certificates** |
| 5 | **Buy a gift certificate for a student** | A parent or loved one picks $25, $50, $100 or $200, enters their own details and the student's, and adds a personal note. The code is shown once on screen and emailed to the student. The page says plainly that this is a class project: **no payment is taken and no card details are collected.** | **Gift Certificates** page |
| 6 | **10% off when paying with a gift certificate** | In the cart, the student enters the code, sees the subtotal, the 10% discount, the total and the balance left, then pays. Prices are always taken from the shop's database, never from the browser, and stock is reduced and the purchase saved to the student's account (so the chatbot can later ask how it worked out). | Cart, "Have a gift certificate?" |
| 7 | **Promotional banner** | A slim banner above the header on every page: "everything bought with a gift certificate is 10% off", linking to the Gift Certificates page. It can be closed with the x for the rest of the visit, so it promotes the offer without nagging. | Top of every page |
| 8 | **"Not what I wanted" button** | When the chatbot puts products on the page and they are the wrong kind, one click tells Handsome Dan. It is in the chat under the results and also in the results bar on the page. It is the shopper's way of teaching the chatbot (see 1.10). | After any chat search that shows products |
| 9 | **Quick-answer buttons in the chat** | Trivia questions and the trivia offer come with buttons (A, B, C, D, or "Yes, let's play!" / "Not now"), so a shopper can answer with one tap, which matters most on a phone. | Chat panel |

### Back end

| # | Improvement | What it does and why it helps |
| --- | --- | --- |
| 10 | **The chatbot learns from its mistakes** | If a shopper says a result was the wrong kind of thing (for example they asked for a **sleeveless** shirt and were shown a **hoodie**), Handsome Dan corrects the search right away, is honest that the shop carries no sleeveless tops, offers the closest style it does carry (short-sleeve t-shirts), and saves a **lesson**: the word "sleeveless" is not a pullover hoodie, try short-sleeve t-shirts. From then on **every** search for that word leaves hoodies out and puts t-shirts first, and the chatbot is told the lesson as a fact about the catalogue. Over time the shop's search gets better at what customers really mean. |
| 11 | **Lessons are protected from misuse** | A lesson has a fixed, checked shape (one word, real garment types from the catalogue, a short note), so a customer cannot teach it anything harmful. It is only saved about styles the shopper was actually shown. It starts as "pending" and is used for everyone once **two different customers** report it (or an admin approves it), so one person cannot quietly change what everybody sees. Admins can see, approve and switch off lessons, and they appear in the feedback report. |
| 12 | **Yale trivia when the chat goes quiet** | After more than a minute with no activity, Handsome Dan opens the chat and offers a quick three-question multiple-choice Yale trivia game, and says the shopper can keep shopping any time. It is offered once per visit. This keeps shoppers company and gives them a reason to stay. |
| 13 | **Trivia that cannot be wrong** | The questions and answers come from a checked list in the shop's code. The chatbot has to read each question out word for word (if it paraphrases, the shop sends it back), and the code, not the AI, decides whether an answer is right. Each answer gets a fun fact and a running score, and after a round Handsome Dan offers to keep playing or to show gear related to the topic. |

**Honest limits.** Gift certificates take no real payment (this is a class project, and the site says so). "Learning" means saved lessons that change the shop's search, not retraining the AI model, and a lesson needs a second customer to confirm it before it affects everyone.

---

## 2. Front-end improvements from earlier problems

| Improvement | What it does and why it helps | Where to see it |
| --- | --- | --- |
| **White product backgrounds** | Many of the original photos had black backgrounds, which hid dark clothing. They were repainted white (originals untouched), so every product reads clearly and the grid looks consistent. A version number on each photo address stops the browser showing an old cached black photo. | Products grid, product pages, cart |
| **A tougher Handsome Dan** | A new cartoon bulldog with some attitude, used as the chat helper and in the footer, so the mascot is on every page. | Footer and chat button |
| **Campaign headline and banner text** | "Lux et Veritas meets swagger & pride" and the new subtitle, with a "Fan favorites" row of four popular styles. | Home page |
| **Live stock on every size** | Each size shows how many are in stock, "Only N left" when it is 5 or fewer, and sold-out sizes are marked and cannot be picked. | A product page, size picker |
| **Friendly size prompts** | If a shopper tries to add to cart without choosing a size, the page scrolls to the size picker and says what is missing instead of failing silently. "Need help with sizing?" opens the chatbot. | A product page |
| **"If you like this, consider..."** | Three similar products, matched on style, color and the size being looked at, each with a one-line reason ("Same style: pullover hoodie · Your size (M) is in stock"). | Bottom of a product page |
| **Search that understands tags** | The Products search looks in names, styles, descriptions, colors and tags, so "berkeley" or "heather gray" works; results are counted and can be sorted by price. | Products page |
| **Cart that remembers** | The cart is saved in the browser and survives a refresh, with a slide-in drawer, a live item count and Remove buttons. | Cart button |
| **Chat results on the page** | When Handsome Dan finds products they appear as cards **on the page being viewed** (photo, price, a line of description). On a product page they fold into a slim bar so the product the shopper clicked stays on screen. | Chat: "show me gray hoodies" |
| **Chat that knows the page** | "Is this in my size?" works, because the chatbot is told which product and size the shopper is looking at. | Chat on a product page |
| **A conversation that comes back** | A logged-in shopper's chat returns when they come back, and Handsome Dan may open by asking how a past purchase worked out. | Log in, open chat |
| **Password help while typing** | The sign-up and password forms tick off each rule as it is met, with Show/Hide buttons, and explain exactly what is wrong. | Create Account, My Account |
| **My Account button** | When logged in, a **My Account** button sits in the menu with a "Hi, name" greeting, so changing a password is one click away instead of buried. | Top menu when logged in |
| **Forgot-password flow** | "Forgot your password?" emails a one-time link that expires in 30 minutes. | Log In page |
| **Accessibility and phones** | A "Skip to content" link, labelled buttons and forms, visible focus outlines, and a Menu button that collapses the navigation on small screens. | Press Tab on any page; narrow the window |

---

## 3. Back-end improvements from earlier problems

| Improvement | What it does and why it helps |
| --- | --- |
| **Next size up and down** | If a size is sold out (or one we do not make, like 3XL), the chatbot says so first and offers **both** the closest larger and closest smaller size that is in stock, with how many are left, instead of a dead end. |
| **No invented prices or stock** | Every price and "N left" the chatbot states is checked against what its tools returned that turn; if it made a number up, the answer is sent back to be fixed. Product cards on the page are filled in from the database by product id, so a card can never show a wrong price or photo. |
| **Customer memory, with limits** | The chatbot knows a logged-in customer's own name and email, and what they bought, only to recommend well. It never sees payment details, phone numbers or addresses, and cannot see anyone else's data. |
| **Follow-up on purchases** | A few days after a purchase, the chatbot asks how it worked out and files the answer (rating, fit, comment). Admins read it in a compiled report (`output/customer_feedback.md`), which shows customers only as a first name and last initial. |
| **Secure accounts** | Passwords are salted PBKDF2 hashes, never stored as text; reset links and logins are stored only as fingerprints; the login cookie is hidden from page scripts; five wrong tries lock an account for 15 minutes; changing a password logs out other devices and emails a confirmation. |
| **Cleaner data** | Consistent naming (t-shirt, short-sleeve, navy blue), filled-in descriptions and tags for the three gray products, and a fixed product-name mismatch, so search and chat find the right things. |
| **Safe and affordable chat** | Each person is limited to 30 messages every 15 minutes, off-topic and unsafe requests get a short friendly redirect, and a message the AI service itself refuses is not saved. |
| **Instructions that update instantly** | The chatbot's instructions live in `backend/prompt/prompt.md` and are re-read on every message, so wording changes apply with no restart. |
| **Tested** | 121 automated tests run in seconds on a throwaway copy of the database and never call the real AI service. |

---

## 4. How each item was checked in the running app

All of these were exercised in a browser against a throwaway copy of the database (so no real customer data was touched).

| Item | What was done | Result |
| --- | --- | --- |
| Category and "Shop for" menus | Chose Ice hockey, then Hoodies | Address became `?category=hoodies&shop=hockey`; two hockey hoodies shown |
| Gift Certificates menu, banner, page | Opened from the menu; bought a $100 certificate | Code shown once; two emails saved to the outbox |
| 10% off in the cart | Logged in, put a $68.00 hoodie in the cart, entered the code | $68.00 became $61.20 ($6.80 off); balance left $38.80; the order appears in the account's purchases; the cart emptied |
| Trivia offer after a quiet minute | Left the page alone for 60 seconds | The chat opened with the offer and "Yes, let's play!" / "Not now" buttons |
| Trivia game | Said yes, answered with the C button | A, B, C, D buttons appeared; "Correct!" plus a fun fact and score |
| "Not what I wanted" | Searched "gray hoodies", clicked the button | The message was sent and Handsome Dan asked what was wrong |
| Learning | Two different customers each said a hoodie was not "sleeveless" | The lesson became active; a third person asking for a sleeveless shirt was shown only short-sleeve t-shirts and told we carry no sleeveless tops |
| Next size up/down | On the Baseball Left Chest Crewneck, asked for XL (sold out) | Offered XXL and L with stock counts |
| White backgrounds, live stock, similar products, skip link, My Account | Opened a product page while logged in | Present: white-background photo, "Only 5 left" labels, three similar products with reasons, skip link, My Account button |
