# HW4 – Campus Customs Website: AI Prompts Log

My own prompts to the vibe coder, one section per problem, logged word for word.

## Index

| Problem | Title | Prompts | Follow-ups? |
| --- | --- | --- | --- |
| 1 | Vibe coder prompts | 1 | no |
| 2 | Analyze the database | 9 | yes (8) |
| 3 | Build the Campus Customs Website | 4 | yes (3) |
| 4 | Create account and login | 6 | yes (5) |
| 5 | PydanticAI agent backend | 2 | no |
| 6 | Tools: product info and stock | 2 | no |
| 7 | Chat search that updates the page | 2 | no |
| 8 | Customer memory | 1 | no |
| 9 | Usability improvements | 1 | no |
| 10 | Style the website | 2 | yes (1) |
| 11 | Site checking (app check) | 1 | no |
| 12 | Audit trail, safety, finish harness | 1 | no |
| 13 | Push to Github and submit the URL | 1 | no |

---

## Problem 1: Vibe coder prompts

### Prompt 1

> Problem 1: Vibe coder prompts. Please keep the ai_prompts.md log updated as we work

---

## Problem 2: Analyze the database

### Prompt 1

> Problem 2: Analyze the database
>
> Let's start output/harness.md
> The first database table is Catalogue, and it contains the following fields:  
> product_id - a unique tag so shop and chatbox can track products precisely
> name - a descriptive title for customers 
> garment_type - because different items meet different customer needs 
> description - data for the chatbot to pull from when answering customer questions
> colors - to refine inventory questions and answers
> search_tags - helpful to anticipate what customers are most likely to ask for, hopefully these get updated as users build the database with submissions
> image_file_path - to make it easy for humans to visualize the product and decide if it's right for them
> price - again, to help customers decide if the transaction is worth their money
>
> The next table is chat_messages and its fields are:
> id - a running list tracking interactions with the chatbot
> user_id - tracking which registered user was having this conversation; good for data on who chatted, what was said vs what was purchased or not 
> role - was it the chatbot or the customer? 
> content - what was actually said, very important for tracking customer questions and ultimately market demand fluctuations
> products_json - what the chatbot actually referenced in answer to a prompt and where the data came from
> created_at - for tracking when chats occured, how long customers engaged for and how long it took to get them a satisfactory answer
>
> Next is inventory:
> id - the very specific product by style and size - crucial for tracking how many of a particular thing a customer may ask for 
> product_id - referencing its unique categorical tag for better answers 
> size - because humans need this, body sizes vary dramatically from person to person 
> quantity - obviously crucial for both chatbot and store to understand what they have, what they're selling lots of and what they need to restock or inform customers are low on quantity
>
> Next database table is sqlite_sequence, and its fields are 
> name - category of data being tracked overall
> seq - I believe this is a summary number of entries per category
>
> Final database table is users, and its fields are 
> id - a number to identify which user in case name or other identifier does not, plus it's a count for how many registrations this thing has got, a good performance metric 
> name - important for identification purposes, customer data and delivering personalized chatbox conversation 
> password_hash - tracking user passwords in an encrypted way so that only the registered person gets access to their account.

### Follow-up 1

> @"/Users/jess/Downloads/data.zip"
> Here's the Zip, it should be filed the same way we did #3. Database file is in there too. Use your corrected versions for what sqlite_sequence and password_hash are. Log this prompt as a followup please

**What was lacking:** I misunderstood sqlite_sequence and misspoke when describing password_hash and Claude helpfully corrected me. Also i did not notice before that garment_type data was a bit messy and it could throw off the chatbot. My followup prompts identified likely trouble spots and dictated a spelling convention where it mattered

### Follow-up 2

> Oh shoot - please update the missing columns in users this way:
> email - to track a unique identifier in case other customer details match 
> created_at - to know how long a certain customer or aggregate customers have had accounts, may also be helpful in reconciling orders or tracking how long between chat and actual order placement 
> first_name - so chatbot can refer to someone casually 
> last_name - also for tracking orders, payment methods and in case someone asks to be referred to as Ms. or Mr. by the chatbot
>
> Also for messy labels please use this convention: 
> t-shirt rather than T-shirt, short-sleeve with a hyphen 
> What else might cause confusion?

**What was lacking:** covered by the note under Follow-up 1 ("What was lacking DID cover follow up 2")

### Follow-up 3

> apply earlier and the following changes to the database please:
>
> 2: use pullover hoodie where applicable, crewneck sweatshirt, quarter-zip pullover, change 1 4 to quarter-zip, fix obvious typos like creqneck. In product names please Title Cases, the above was for garment_type only. 
>
> Refine repeated tags that differ only by capitalization; use all lower case. 
>
> Use navy blue only 
>
> If the chatbot is asked about a size we don't have, it should offer both the available next size up and available next size down. 
>
> Can you make emails NOT case-sensitive? 
>
> I don't understand the problem with first and last name 
>
> What was lacking DID cover follow up 2.

**What was lacking:** Database had incomplete or incorrect fields and later prompts corrected them for better results with the chatbot later

### Follow-up 4

> in harness.md  - the chatbot should trust first_name and last_name if there's a discrepancy. 
>
> Stub descriptions: 3 products have a placeholder description like “Vision blocked; filename-based stub”. The chatbot would repeat that to customers. Do you want me to list them? yes please

**What was lacking:** same note as Follow-up 3 (one note covers Follow-ups 3, 4 and 5)

### Follow-up 5

> delete "Vision blocked; filename-based stub." From all 3. 
>
> Colors - all 3 are heather grey
>
> double check that against what you see and update the database.

**What was lacking:** same note as Follow-up 3 (one note covers Follow-ups 3, 4 and 5)

### Follow-up 6

> yes write descriptions for the 3 gray products

**What was lacking:** covered by the note under Follow-up 3 ("earlier note covers them")

### Follow-up 7

> yes, write proper tags for them

**What was lacking:** covered by the note under Follow-up 3 ("earlier note covers them")

### Follow-up 8

> earlier note covers them
>
> hyphenate tags to match garment types

**What was lacking:** covered by the note under Follow-up 3 ("both followups are covered in previous sentences")

---

## Problem 3: Build the Campus Customs Website

### Prompt 1

> On to Problem 3: Build the Campus Customs Website
>
> OK, we’re going to build the front end of a student merch website using React + Vite + TypeScript. If you need more info to use those, please let me know. Big picture, we need a top nav bar that elegantly links to main pages of the site, including Home, Products, About Us, Log In and Create Account.
> While we’re at it, let’s build backend/main.py and start a simple FastAPI app to serve products and images
>
> Now, about those front end web pages…
> All design elements should reflect Yale colors, branding, logos, campus photography and the latin motto, Lux et veritas (confirm that’s correct first, please.) Also put the mascot bulldog on every page please.
> Home page banner text:
> where Lux et Veritas meets comfort, style and convenience
> Join generations of Yalies in proudly displaying your Bulldog Blue swagger!
>
> About Us page:
> Campus Customs has been Yale University’s original licensed merchandise boutique since 1975!
> We learn from YOU and grow our offerings with each generation that passes through these hallowed halls - this ain’t your granddaddy’s Yale sweater.
>
> Products page:
> Display each product and its associated image (per image path in the database) along with its product info: title, price, and a button underneath that opens a full product page. Also clicking on the photo should open the full product page
> On each individual full product page, the product image should display large on the left, plus all product information we have on the right including the description, how many we have of each size in stock and the price. Follow industry design best practices on product and information placement, size and add to cart button design, plus any other critical pieces that drive customer online interaction.
> A chatbot interface should be in the bottom right and pop up as a floating panel friendly cartoon bulldog with a speech bubble saying “Need help?”
>
> At the bottom, add a feature: If you like this, consider… and then populate 3 other products whose style, color or size match what the customer was viewing.

### Follow-up 1

> ok amazing - can you please try a different cartoon bulldog for Dan; make him look a little tough.
>
> also can all the product backgrounds be on white?
>
> change banner text to "where Lux et Veritas meets swagger and pride"
> then "where generations of Yalies go for their Bulldog Blues"

**What was lacking:** once I saw product photos displayed I realized we needed some different design choices.

### Follow-up 2

> [screenshot attached: three products with black backgrounds]
>
> still a bunch of black backgrounds

**What was lacking:** same note as Follow-up 1 (one note covers Follow-ups 1 and 2)

### Follow-up 3

> beautiful, Please update headline to say "Lux et Veritas meets swagger & pride"
>
> For What was lacking -- once I saw product photos displayed I realized we needed some different design choices.

**What was lacking:** covered by the note under Follow-up 1 ("both followups are covered in previous sentences")

---

## Problem 4: Create account and login

### Prompt 1

> Ok next Problem 4: Create account and login
> We’re going to create a mechanism for users to create an account with first name, last name, email and password. Include a second field where they have to confirm their passwords and they have to match. Use typical password security protocol rules for choosing their password, and when it’s stored in the database hash and salt the passwords so that people and AI can’t hack it.
> When returning customers login, they only need an email and password and if they forgot it, they can send a password reset email to the address on file.

### Follow-up 1

> i forgot to mention that new accounts should be stored in the users table in the db

**What was lacking:** I needed to confirm that new accounts go into the user table, I asked it to add a My Account button for easy password changes, and needed to confirm the hash function was set up correctly.

### Follow-up 2

> I should be able to log in with test@campuscustoms.yale.edu and a test password but i'm getting error

**What was lacking:** my new password security protocols meant that the test passwords were failing checks.

### Follow-up 3

> it works. Can you add a "my account" button when users are logged in so it's easy to update their passwrd

**What was lacking:** same note as Follow-up 1 (one note covers Follow-ups 1, 3 and 4)

### Follow-up 4

> can you confirm hash settings match PFKDF-HMAC-SHA256, 120,000 iterations and stored as pbkdf2_sha256$salt$hash

**What was lacking:** same note as Follow-up 1 (one note covers Follow-ups 1, 3 and 4)

### Follow-up 5

> in the output/harness, please document how auth works (username and password protection) and include the sections above: security around changing a password and testing.

**What was lacking:** no note needed ("don't worry about Problem 4, Follow-up 5")

---

## Problem 5: PydanticAI agent backend

### Prompt 1

> Problem 5: PydanticAI agent backend
>
> ok so the shop chatbot Should be an pedantic AI agent behind fast API. Please put the API app in backend/main.py.
>
> We need a few files, including backend /prompt/prompt.md for system prompt. We need backend /agent.py for agent entry and wiring. We need backend /tools.py for tools that the agent can use, and backend /models.py for the pedantic structured types. In main.py, we need a chat route, so a message from the website returns a reply from the agent and whatever else it needs to answer questions from products /auth. Let me know if you need an API key for this.

### Prompt 2

> Let’s get started in prompts/prompt.md - we will be building campus customs voice and safety basics.
> Don’t let the agent do anything weird beyond being a helpful chatbot for people considering buying merchandise from the store. The chatbot should be friendly, helpful and welcoming. But they can’t access payment data like credit cards or contact information. They can reference past purchases from accounts to recommend products they think customers will like. If a user asks a question beyond the scope of this store, cheerfully redirect. Ditto for all other questions that aren’t topical or apprrporaite.
> The backend should run from the backend folder like this: uvicorn main:app --reload --port 8000
> And please note in the output/harness how the front end talks to FastAPIand how the agent is loaded in terms of prompt file and model

---

## Problem 6: Tools: product info and stock

### Prompt 1

> Please give the agent everything it needs to look up real information from the campus customs database. It will need product description, price, how many are in stock, by which size. It probably needs to see the tags to know more about the items available. Please don't invent prices, don't invent quantities. As we spoke about before, if a size is out of stock, say so clearly and suggest the next closest alternative for the customer. Also, expand prompt/promptMD so the agent knows to call it up for price and stock questions. Add or update return types in models.py. I think we've handled all of this in previous prompts. Now in the output/harness.md, put all the tools that the agent has. And also let me see them in a list so that I can explain which fields I chose for lookup results. I need that for this problem.

**What was lacking:** nothing was missing. All of the missing data had been handled in a previous problem prompt and conversation.

### Prompt 2

> ok good - please add the full section "The agent’s seven tools" and all of its columns to the output/harness
>
> I did not need a followup prompt, so nothing was missing from the first. You can add a sentence that all missing data had been handled in a previous problem prompt and conversation

---

## Problem 7: Chat search that updates the page

### Prompt 1

> on to problem 7: Chat search that updates the page
>
> Oh, this is going to be cool. Here's a new feature that we're going to add. When a customer asks about a certain type of item, have the agent search the catalog, and the website should dynamically show matching items as product cards displaying on the page, including their image, name, price, and short information about it.
>
> This should be an API contract, so the agent pulls the information about product matches from the database and hands it to the front end to render them visually on the page that the customer is looking at. Also, after those dynamic product cards are loaded by this new feature, double check that it didn't break the single item pages. And when a customer goes to look at a product card, including the one that the chat just put up, it should still open the full detail view. Please update prompt/promptmd and output/harnessmd so it's clear how search results reach the page for this feature.

### Prompt 2

> Please fix the school of architecture crewneck discrepancy

---

## Problem 8: Customer memory

### Prompt 1

> that was part of problem 7 - you can log it and we're all done with problem 7.
>
> Problem 8: Customer memory
>
> The chatbot should know who is chatting with them - their name and email - so many sure that’s among the tools the agent can reference. Like we said before, it should also know something about their purchase history only to make good recommendations. Guests who are not logged in can chat, but only logged in users have their chats saved. Please document in the output/harness how that history is stored, what customer fields the agent sees and how the page context and content info is passed to the chatbot.
> The chatbot should also know enough about the page that the customer is on to be able to answer questions about what they’re looking at. It sounds like the agent context should have code that allows them to see the page being currently displayed and reference database info about it.
> To make that happen, each logged-in chat should be saved in a database table appropriately named, and puled back up when they log back in so it’s like a conversation they are picking back up. Have the chatbot ask how the previous product worked out for them, if applicable, and file that feedback into the database and compile it as customer feedback that admins can reference later.

---

## Problem 9: Usability improvements

### Prompt 1

> On to problem 9
> As you're building these things, please write output/usability.md. I want it to reflect the following changes but ALSO all of the improvements I've made over past prompts beyond the homework requirements, to both the front end and the back end. I want credit for everything from white backgrounds to improve product visibility, suggesting next sizes up or down, the My Account button for ease of password management, etc. Make sure they all, including the 4 below, show up in the running app.
> In addition, on the front end, some new improvements:
> - On the Products main nav page, please have a dropdown that sorts products into categories customers are most likely to search for: Hoodies, T-shirts, Jackets, etc. Please also include a drop down feature to sort by school or sport or other categories that people belong to that they might want to buy merchandise for. This makes it easy for folks to find what they love.
> - Have a gift certificate nav bar item as well, and create a function for parents or loved ones to buy credits or digital gift cards so their students can shop for something they like. Purchases made with these gift cards get 10% off, so be sure to promote that on a banner to drive sales.
> On the back end:
> - when an agent has been sitting idle for more than a minute, have it offer to play a Yale trivia multi-choice game with the user to engage them and keep them shopping.
> - Also please have the agent learn from past mistakes - if someone asks for a sleeveless shirt and it returns a hoodie, make sure that it's learning the differences and correcting its mistakes as it goes so this gets smarter over time.

---

## Problem 10: Style the website

### Prompt 1

> Now problem 10: Style the website
> Document these changes and previous design changes and upgrades we made in prior prompts - put it in output/design.md.
> When you enter the store, have yale style wrought iron doors open up in front of you - so that it feels experiential and Ivy League.
> Add a scrolling banner of the Colleges and schools in a Yale stylized way so customers can see their school and feel a kinship.
> Put a watermark of the yale logo in the background of the products section banner, behind the products, because it would look pretty
> On the About Us page add photos of modern Yale students in merchandise for sale in our shop - because we need some actual humans on this site!

### Follow-up

> no how about this: use an illstration of handsome dan wearing our merch instead of photos of student

**What was lacking:** I had grand visions of images of students but actually prefer an illustrated Handsome Dan so we made that change

---

## Problem 11: Site checking (app check)

### Prompt 1

> Ok now Problem 11 - Site checking (app check)
>
> Please create an output/app_check.html and document 3 important screenshots - first, chat checking the inventory level of a piece of merch with a price
> (2) the dynamic search result cards that appear when someone mentions a category to the chat bot
> (3) also please screenshot the gift certificate feature
> And HTML should include a heading for each check and each screenshot - and put each screenshot image file output/app_check_images link from app_check.html with relative paths and file names
> I need to add one or two sentences for each about what each proves and demonstrates

---

## Problem 12: Audit trail, safety, finish harness

### Prompt 1

> On to Problem 12: audit trail, safety, finish harness
>
> we need an append-only output/audit_trail.json of agent-loop activity including time, tool name, short args/results and stop reason that doesn't wipe between runs.
>
> Also let's add safety rules for the agent prompts/prompts.md: basically, don't be weird or creepy and stick to the defined role, please. Refer back to earlier safety prompts. Add anything resronable that I haven't thought of, please.
>
> Finish output/harness.md to clarify for observers and graders how this whole system works and what the upgrades are. Please include model fields in models.py and why i chose them. Ask if this is not clear. Detail the rools and abilities we've built, highlighting extra capacities; outline the safety rules in place including new ones; plus specs: loop limits, result caps, models and how to run the front and back ends

---

## Problem 13: Push to Github and submit the URL

### Prompt 1

> On to Problem 13: Push to Github and submit the URL.
>
> we nede to take hw4 with everything in it and push it to github public repository. leave out  the .env, campus_customs datavase or product images from the repo. Use .gitignore and .env.example with placeholders
>
> Confirm that the agent is running on 4 files and the readme explains how to run the front and back ends after placing hte data pack
>
> please show me the file layout so i can check it
