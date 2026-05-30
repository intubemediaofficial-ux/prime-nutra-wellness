# PrimeNutra Wellness 🌿

A green, health-conscious **organic e-commerce website** for herbal supplements, teas,
superfoods and wellness combos — inspired by leading organic brands and built as a fast,
fully static site (HTML + CSS + vanilla JS, no build step).

## Features

- **Home** — hero, shop-by-category, shop-by-health-concern, best sellers, combos, promos, testimonials, newsletter
- **Shop** — live filtering by category / health concern / price + search + sorting
- **Product detail** — size & quantity selection, benefits, related products, WhatsApp order
- **Cart** — slide-in drawer, persistent via `localStorage`
- **Checkout** — shipping form, automatic discount tiers, COD / UPI, WhatsApp order option, order confirmation
- **Wishlist**, **About**, **Wellness Blog**, **Contact + FAQ**
- Mobile-responsive, accessible, SEO meta tags, no external image dependencies

## Project structure

```
index.html         Home
shop.html          Catalogue with filters
product.html       Product detail (?id=...)
checkout.html      Checkout + order confirmation
wishlist.html      Saved items
about.html         Brand story
blog.html          Wellness articles
contact.html       Contact form + FAQ
css/styles.css     Theme & layout
js/products.js     Product / category / concern data
js/app.js          Header, footer, cart, wishlist, UI logic
```

## Run locally

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Customisation

- **Products / categories / concerns** — edit `js/products.js`
- **WhatsApp order number** — set `WA_NUMBER` in `js/app.js` (and the `wa.me` links in `product.html` / `checkout.html`)
- **Theme colours** — CSS variables at the top of `css/styles.css`

## Deploy

The site is fully static and can be hosted on any static host (GitHub Pages, Netlify,
Vercel, S3, etc.). Production domain: **primenutrawellness.in**.
