# Design of the Campus Customs website

How the site looks and why. Section 1 is the design system the whole site is built on. Section 2 lists the design changes made in earlier problems. Section 3 is the Problem 10 styling. Section 4 is what is still waiting on you. Everything lives in `frontend/src/index.css` (styles) and the files named below.

## 1. The design system

| Choice | What it is | Why |
| --- | --- | --- |
| **Colors** | Yale blue `#00356b` (main), a darker blue `#00244a` for bands, light blue `#63aaff` for accents on dark, white and a cool gray page background. Green is used only for good news (stock, discounts), orange for warnings, red for errors. | Looks like Yale at first glance and keeps one strong color. |
| **Type** | A Baskerville/Georgia serif for headlines, mottos and prices of importance, a clean system sans-serif for everything else. | The serif gives the Ivy League feel; the sans keeps forms and chat easy to read. |
| **Shapes** | Rounded 10px cards with a thin gray border and a soft blue-tinted shadow; one filled blue button style and one outlined style. | Calm and consistent, so products stand out, not the frame. |
| **Layout** | A centered column up to about 1180px, responsive grids (4, 3, 2 and 1 columns), and a Menu button that collapses the navigation on phones. | Works on a laptop and a phone. |
| **Accessibility** | A "Skip to content" link, labelled buttons and form fields, visible focus outlines, and animation switched off for people who ask their device for reduced motion. | Everyone can shop. |

## 2. Design changes from earlier prompts

| Change | Details | Where |
| --- | --- | --- |
| **Home page** | A hero with a campus photo of Harkness Tower under a blue wash, the headline "Lux et Veritas meets swagger & pride" and the subtitle "where generations of Yalies go for their Bulldog Blues", then four Fan favorites and a full-width motto band over the Sterling Library photo. | `pages/Home.tsx`, `.hero`, `.motto-banner` |
| **Campus photography** | Real photos of Harkness Tower, Sterling Memorial Library and Old Campus (credited in the footer), used as tinted backgrounds so text stays readable. | `public/campus/` |
| **Crest and Handsome Dan** | A hand-drawn shield crest for the logo, and a cartoon English bulldog. After the first version, Dan was redrawn tougher: heavy brow, wide jaw, underbite, spiked collar and a Yale-blue sweater, with a raised-fist pose in the footer so he is on every page. These are illustrations for a class project, not Yale's official marks. | `components/Art.tsx`, `Footer.tsx` |
| **White product backgrounds** | Many photos had black backgrounds that hid dark clothing. They were repainted white (originals kept), and each photo address carries a version number so browsers never show an old black copy. Cards then look like a clean catalogue. | `backend/whiten_images.py`, `catalogue.image_url` |
| **Product cards** | One card used everywhere: photo, style label, name, price, optional one-line description or "Sold out right now" note, and a View product button. The same card shows in the grid, in "If you like this, consider...", and for chatbot results. | `components/ProductCard.tsx` |
| **Product page** | Large photo, price, live availability, a size picker where each size shows its stock ("Only 5 left" in warm orange, sold out grayed and disabled), quantity stepper, Add to cart with an "added" confirmation, breadcrumbs and similar products. | `pages/ProductPage.tsx` |
| **Products page tools** | Search, sort, result count, plus the Category and Shop for menus from Problem 9. | `pages/Products.tsx` |
| **Chat helper** | A round bulldog button with a "Need help?" bubble, a panel in Yale blue, and chatbot product results drawn as cards on the page (a slim bar on product pages so the product stays in view). | `components/ChatWidget.tsx`, `ChatResults.tsx` |
| **Accounts** | Centered form cards with a blue top edge, a live checklist for password rules, Show/Hide buttons, and a "Hi, name" greeting with a My Account button once logged in. | `pages/AccountForms.tsx`, `Header.tsx` |
| **Cart drawer** | A slide-in panel with item photos, quantities, remove buttons, a subtotal and (Problem 9) the gift certificate box with the 10% off breakdown. | `components/CartDrawer.tsx` |
| **Gift banner** | A soft gold strip above the header promoting 10% off with a gift certificate; it can be closed. | `components/GiftBanner.tsx` |

## 3. Problem 10: styling the website

### 3.1 Wrought-iron entrance gates (`components/EntryDoors.tsx`)

- **What the shopper sees:** the first time they open the site in a browser tab, a pair of black wrought-iron gates stands closed across the whole screen: spear-topped bars, scrolled rails, rivets, brass-colored handle rings. A blue plaque in the middle reads "Campus Customs · Since 1975 / Lux et Veritas" with an **Enter the store** button. Choosing it swings the two gate leaves open (a 3D hinge, about two seconds) to reveal the shop, while the plaque fades.
- **Built from:** drawings in SVG (no image files), turned open with a CSS 3D rotation.
- **Considerate details:** it shows once per browser tab (not on every page or reload), it opens by itself after 6 seconds or on Escape so nobody can get stuck, the button gets keyboard focus, and for people with reduced motion the gates simply disappear.

### 3.2 Scrolling college and school ribbon (`components/CollegeMarquee.tsx`)

- **What the shopper sees:** a deep-blue ribbon under the home page hero, slowly scrolling the 11 residential colleges and 11 professional schools, each with a small shield and a COLLEGE or SCHOOL label in small capitals ("Berkeley", "Law", "Management"...).
- **Kinship:** every name is a link that opens the Products page already filtered to that college or school (the "Shop for" menu), so a student lands on gear for their own community.
- **Considerate details:** it pauses when hovered or focused, the repeated copy used for the endless loop is hidden from screen readers and the keyboard, and with reduced motion it becomes a plain ribbon that can be scrolled by hand.

### 3.3 Crest watermark on the Products page (`pages/Products.tsx`)

- The Products page now opens with a blue banner over the Sterling Library photo (matching About Us), with a faint crest behind its title, and a large, very light crest sits behind the product grid so it shows through between the cards.
- It uses the site's own crest drawing, not Yale's official logo (see section 4). It cannot be clicked and does not get in the way of the cards.

### 3.4 Handsome Dan modelling the merchandise on the About Us page (`pages/About.tsx`, `components/Art.tsx`)

- A new **Handsome Dan wears it best** section with four cards, each showing the mascot illustrated in a real product from the shop: the Basic Hoodie Big Yale (gray hoodie with the hood bunched at his neck), the Boola Boola T-Shirt (gray tee with furry bare arms), the Berkeley Quarter-Zip (blue with a zip and light-blue collar stripe) and the Yale Sports Hoodie Hockey (with a hockey stick over his shoulder). Each sits in a little scene (sky, grass, brick, ice). A caption names where he is and links to that product.
- The first plan was photos of real students. It was changed to illustrations so the page has a face with no photo permissions or privacy questions, and so it matches the cartoon mascot used everywhere else. The outfits are a new `outfit` option on the existing `Bulldog` drawing (`sweater`, `hoodie`, `tee`, `quarterzip`, `hockey`), so more looks can be added by drawing one more outfit.

## 4. Cautions

- **Yale's logo:** the watermark and logo are the site's own illustrated crest. Yale's real logo is a trademark, and this is a class project that is "not an official Yale University website" (the footer says so), so I did not use the real mark. If you have permission to use it, replace the `Crest` drawing in `components/Art.tsx` and every place it appears updates.

## 5. How it was checked

In a browser on the running site: the gates appear closed with the plaque and button on a first visit, the button removes them, they do not return after that in the same tab, and the open animation's CSS applies the 3D rotation (checked by reading the computed transform); the ribbon renders all 44 entries (22 shown plus the hidden loop copy), each a link to a filtered Products page; the Products banner and both crest watermarks show; and About Us shows four Handsome Dan illustrations in different merchandise, each with a caption linking to its product. Type-checking passes and the 121 backend tests still pass.
