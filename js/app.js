/* PrimeNutra Wellness — shared app logic: header/footer, cart, wishlist, UI */
(function () {
  "use strict";

  const STORE = "pnw_cart_v1";
  const WISH = "pnw_wish_v1";
  const WA_NUMBER = "919999999999"; // WhatsApp order number (placeholder)

  // Soft per-category background gradients for product media tiles
  const CAT_BG = {
    teas:        "linear-gradient(135deg,#e9f7ef,#cdeede)",
    supplements: "linear-gradient(135deg,#eef3ff,#dbe6ff)",
    superfoods:  "linear-gradient(135deg,#e7f6ed,#c7ecd4)",
    foods:       "linear-gradient(135deg,#fff5e1,#ffe7bd)",
    personalcare:"linear-gradient(135deg,#eafaf3,#d4f0e6)",
    combos:      "linear-gradient(135deg,#f1ecff,#e0d6ff)",
  };
  window.catBg = (c) => CAT_BG[c] || "linear-gradient(135deg,#e7f6ed,#cdeede)";

  /* ---------------- storage helpers ---------------- */
  const read = (k) => { try { return JSON.parse(localStorage.getItem(k)) || []; } catch (e) { return []; } };
  const write = (k, v) => localStorage.setItem(k, JSON.stringify(v));
  const getCart = () => read(STORE);
  const setCart = (c) => { write(STORE, c); renderCart(); updateCounts(); };
  const getWish = () => read(WISH);
  const setWish = (w) => { write(WISH, w); updateCounts(); };

  window.PNW = { getCart, setCart, getWish, setWish, addToCart, toast, formatINR };

  function formatINR(n) { return "₹" + Number(n).toLocaleString("en-IN"); }

  function addToCart(id, size, qty) {
    const p = getProduct(id); if (!p) return;
    size = size || (p.sizes && p.sizes[0]) || "Default";
    qty = qty || 1;
    const cart = getCart();
    const key = id + "|" + size;
    const existing = cart.find((i) => i.key === key);
    if (existing) existing.qty += qty;
    else cart.push({ key, id, size, qty });
    setCart(cart);
    toast(p.name + " added to cart");
    openDrawer();
  }

  function changeQty(key, delta) {
    const cart = getCart();
    const item = cart.find((i) => i.key === key);
    if (!item) return;
    item.qty += delta;
    const next = cart.filter((i) => i.qty > 0);
    setCart(next);
  }
  function removeItem(key) { setCart(getCart().filter((i) => i.key !== key)); }

  function cartTotal() {
    return getCart().reduce((s, i) => { const p = getProduct(i.id); return s + (p ? p.price * i.qty : 0); }, 0);
  }
  function cartCount() { return getCart().reduce((s, i) => s + i.qty, 0); }

  window.toggleWish = function (id) {
    let w = getWish();
    if (w.includes(id)) w = w.filter((x) => x !== id);
    else { w.push(id); toast("Added to wishlist"); }
    setWish(w);
    document.querySelectorAll('[data-wish="' + id + '"]').forEach((el) => el.classList.toggle("active", getWish().includes(id)));
  };

  /* ---------------- toast ---------------- */
  let toastTimer;
  function toast(msg) {
    let t = document.getElementById("toast");
    if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; document.body.appendChild(t); }
    t.textContent = msg; t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 2200);
  }

  /* ---------------- counts ---------------- */
  function updateCounts() {
    const c = cartCount();
    document.querySelectorAll("[data-cart-count]").forEach((el) => { el.textContent = c; el.style.display = c ? "grid" : "none"; });
    const w = getWish().length;
    document.querySelectorAll("[data-wish-count]").forEach((el) => { el.textContent = w; el.style.display = w ? "grid" : "none"; });
  }

  /* ---------------- product card ---------------- */
  window.productCard = function (p) {
    const disc = discountPct(p);
    const wished = getWish().includes(p.id) ? " active" : "";
    return (
      '<article class="card">' +
        '<a class="card__media" style="background:' + window.catBg(p.category) + '" href="product.html?id=' + p.id + '">' +
          (p.badge ? '<span class="card__badge">' + p.badge + "</span>" : "") +
          (disc > 0 ? '<span class="card__disc">' + disc + "% OFF</span>" : "") +
          (p.image ? '<img class="card__img" src="' + p.image + '" alt="' + p.name + '" loading="lazy">' : '<span class="em">' + p.emoji + "</span>") +
        "</a>" +
        '<button class="card__wish' + wished + '" data-wish="' + p.id + '" onclick="toggleWish(\'' + p.id + '\')" aria-label="wishlist">♥</button>' +
        '<div class="card__body">' +
          '<span class="card__cat">' + categoryName(p.category) + "</span>" +
          '<a class="card__title" href="product.html?id=' + p.id + '">' + p.name + "</a>" +
          '<div class="card__rating">★ ' + p.rating + ' <span>(' + p.reviews + ")</span></div>" +
          '<div class="card__price"><b>' + formatINR(p.price) + "</b>" + (disc > 0 ? "<s>" + formatINR(p.mrp) + "</s>" : "") + "</div>" +
          '<div class="card__actions">' +
            '<button class="btn btn--primary btn--sm" onclick="PNW.addToCart(\'' + p.id + '\')">Add to Cart</button>' +
            '<a class="btn btn--ghost btn--sm" href="product.html?id=' + p.id + '">View</a>' +
          "</div>" +
        "</div>" +
      "</article>"
    );
  };

  window.renderGrid = function (selector, list) {
    const el = document.querySelector(selector);
    if (!el) return;
    el.innerHTML = list.length ? list.map(window.productCard).join("") : '<div class="empty">No products found. Try clearing filters.</div>';
  };

  /* ---------------- header / footer ---------------- */
  function catLink(c) {
    return '<a href="shop.html?category=' + c.id + '"><span class="em">' + c.emoji + '</span><span><b>' + c.name + "</b><span>" + c.blurb + "</span></span></a>";
  }
  function concernLink(c) {
    return '<a href="shop.html?concern=' + c.id + '"><span class="em">' + c.emoji + '</span><span><b>' + c.name + "</b><span>" + c.blurb + "</span></span></a>";
  }

  function headerHTML() {
    return (
      '<div class="announce"><div class="announce__track">' +
        repeatAnnounce() + repeatAnnounce() +
      "</div></div>" +
      '<header class="header"><div class="container header__row">' +
        '<button class="icon-btn hamburger" id="hamburger" aria-label="menu">☰</button>' +
        '<a class="logo" href="index.html"><span class="logo__mark">🌿</span><span>PrimeNutra<small>Wellness</small></span></a>' +
        '<nav class="nav" id="nav">' +
          '<div class="nav__item"><span class="nav__link js-acc">Shop by Category ▾</span>' +
            '<div class="dropdown dropdown--wide">' + CATEGORIES.map(catLink).join("") + "</div></div>" +
          '<div class="nav__item"><span class="nav__link js-acc">Health Concern ▾</span>' +
            '<div class="dropdown dropdown--wide">' + CONCERNS.map(concernLink).join("") + "</div></div>" +
          '<div class="nav__item"><a class="nav__link" href="shop.html?category=combos">Combos &amp; Kits</a></div>' +
          '<div class="nav__item"><a class="nav__link" href="blog.html">Wellness Blog</a></div>' +
          '<div class="nav__item"><a class="nav__link" href="about.html">About</a></div>' +
          '<div class="nav__item"><a class="nav__link" href="contact.html">Contact</a></div>' +
        "</nav>" +
        '<div class="header__actions">' +
          '<button class="icon-btn" onclick="location.href=\'shop.html\'" aria-label="search">🔍</button>' +
          '<button class="icon-btn" onclick="location.href=\'wishlist.html\'" aria-label="wishlist">♥<span class="badge-count" data-wish-count style="display:none">0</span></button>' +
          '<button class="icon-btn" id="cartBtn" aria-label="cart">🛒<span class="badge-count" data-cart-count style="display:none">0</span></button>' +
          '<button class="icon-btn auth-login-btn" id="authLoginBtn" onclick="PNW.showLogin()" aria-label="login" title="Login">👤</button>' +
          '<a class="icon-btn auth-account-btn" id="authAccountBtn" href="account.html" style="display:none" aria-label="account" title="My Account">👤</a>' +
        "</div>" +
      "</div></header>"
    );
  }

  function repeatAnnounce() {
    const items = [
      "🚚 Free delivery across India",
      "💵 Cash on Delivery available",
      "🎁 8% off on orders above ₹999",
      "🎉 12% off + free gift above ₹1599",
      "🌿 100% certified organic",
    ];
    return '<div class="announce__track" style="animation:none;display:contents">' +
      items.map((i) => "<span>" + i + "</span>").join("") + "</div>";
  }

  function drawerHTML() {
    return (
      '<div class="drawer-overlay" id="drawerOverlay"></div>' +
      '<aside class="drawer" id="drawer" aria-label="cart">' +
        '<div class="drawer__head"><h3>Your Cart</h3><button class="icon-btn" id="drawerClose">✕</button></div>' +
        '<div class="drawer__items" id="drawerItems"></div>' +
        '<div class="drawer__foot">' +
          '<div class="line"><span>Subtotal</span><span class="total" id="drawerTotal">₹0</span></div>' +
          '<a class="btn btn--primary btn--block" href="checkout.html">Checkout</a>' +
          '<a class="btn btn--ghost btn--block" href="shop.html" style="margin-top:8px">Continue Shopping</a>' +
        "</div>" +
      "</aside>"
    );
  }

  function footerHTML() {
    const y = new Date().getFullYear();
    return (
      '<footer class="footer"><div class="container">' +
        '<div class="footer__grid">' +
          '<div class="footer__brand"><a class="logo" href="index.html"><span class="logo__mark">🌿</span><span>PrimeNutra<small>Wellness</small></span></a>' +
            "<p>Pure, certified-organic herbal supplements, teas and superfoods to help you live healthier — naturally.</p>" +
            '<div class="social"><a href="#" aria-label="facebook">f</a><a href="#" aria-label="instagram">◎</a><a href="#" aria-label="youtube">▶</a><a href="#" aria-label="x">✕</a></div></div>' +
          "<div><h4>Shop</h4>" + CATEGORIES.map((c) => '<a href="shop.html?category=' + c.id + '">' + c.name + "</a>").join("") + "</div>" +
          '<div><h4>Health Concerns</h4>' + CONCERNS.slice(0, 6).map((c) => '<a href="shop.html?concern=' + c.id + '">' + c.name + "</a>").join("") + "</div>" +
          '<div><h4>Company</h4><a href="about.html">About Us</a><a href="blog.html">Wellness Blog</a><a href="contact.html">Contact</a><a href="contact.html#faq">FAQ</a><a href="contact.html">Shipping &amp; Returns</a></div>' +
        "</div>" +
        '<div class="footer__bottom"><span>© ' + y + ' PrimeNutra Wellness. All rights reserved.</span>' +
          "<span>Made with 🌿 for a healthier India · primenutrawellness.in</span></div>" +
      "</div></footer>"
    );
  }

  /* ---------------- cart drawer render ---------------- */
  function renderCart() {
    const wrap = document.getElementById("drawerItems");
    if (!wrap) return;
    const cart = getCart();
    if (!cart.length) { wrap.innerHTML = '<div class="empty">Your cart is empty 🛒<br><br>Add some wellness essentials!</div>'; }
    else {
      wrap.innerHTML = cart.map((i) => {
        const p = getProduct(i.id); if (!p) return "";
        return (
          '<div class="cart-row">' +
            '<div class="thumb" style="background:' + window.catBg(p.category) + '">' + p.emoji + "</div>" +
            "<div><b>" + p.name + "</b><small>" + i.size + " · " + formatINR(p.price) + "</small>" +
              '<div class="qty"><button onclick="PNW._q(\'' + i.key + '\',-1)">−</button><span>' + i.qty + "</span><button onclick=\"PNW._q('" + i.key + "',1)\">+</button></div></div>" +
            '<div style="text-align:right"><b>' + formatINR(p.price * i.qty) + '</b><br><button class="rm" onclick="PNW._rm(\'' + i.key + "')\">Remove</button></div>" +
          "</div>"
        );
      }).join("");
    }
    const tot = document.getElementById("drawerTotal");
    if (tot) tot.textContent = formatINR(cartTotal());
  }
  PNW._q = changeQty; PNW._rm = removeItem;

  /* ---------------- drawer open/close ---------------- */
  function openDrawer() {
    const d = document.getElementById("drawer"), o = document.getElementById("drawerOverlay");
    if (d) d.classList.add("open"); if (o) o.classList.add("open");
  }
  function closeDrawer() {
    const d = document.getElementById("drawer"), o = document.getElementById("drawerOverlay");
    if (d) d.classList.remove("open"); if (o) o.classList.remove("open");
  }
  window.PNW.openDrawer = openDrawer;

  /* ---------------- OTP Login Modal ---------------- */
  function showLogin() {
    // Remove existing modal
    var old = document.getElementById("loginModal");
    if (old) old.remove();
    var modal = document.createElement("div");
    modal.id = "loginModal";
    modal.className = "login-modal-bg";
    modal.innerHTML = '<div class="login-modal">' +
      '<button class="login-modal__close" onclick="document.getElementById(\'loginModal\').remove()">&times;</button>' +
      '<h2>🌿 Login / Sign Up</h2>' +
      '<p>Enter your mobile number to continue</p>' +
      '<div id="lm_step1">' +
        '<div class="field"><label>Mobile Number</label><input id="lm_phone" type="tel" maxlength="10" placeholder="e.g. 9876543210"></div>' +
        '<button class="btn btn--primary btn--block" id="lm_sendOtp">Send OTP</button>' +
      '</div>' +
      '<div id="lm_step2" style="display:none">' +
        '<div class="field"><label>Enter OTP sent to <span id="lm_ph2"></span></label><input id="lm_otp" type="text" maxlength="6" placeholder="6-digit OTP"></div>' +
        '<button class="btn btn--primary btn--block" id="lm_verify">Verify & Login</button>' +
        '<button class="btn btn--ghost btn--block" style="margin-top:8px" id="lm_back">Change Number</button>' +
      '</div>' +
      '<div id="lm_msg" class="lm_msg"></div>' +
      '</div>';
    document.body.appendChild(modal);
    modal.addEventListener("click", function(e) { if (e.target === modal) modal.remove(); });
    document.getElementById("lm_sendOtp").onclick = function() {
      var phone = document.getElementById("lm_phone").value.replace(/\D/g,"");
      if (phone.length < 10) { document.getElementById("lm_msg").textContent = "Enter valid 10-digit number"; return; }
      document.getElementById("lm_msg").textContent = "Sending OTP...";
      window.PNW_AUTH.sendOTP(phone).then(function(r) {
        document.getElementById("lm_step1").style.display = "none";
        document.getElementById("lm_step2").style.display = "";
        document.getElementById("lm_ph2").textContent = phone;
        document.getElementById("lm_msg").textContent = r.otp ? "Dev OTP: " + r.otp : "OTP sent!";
        document.getElementById("lm_otp").focus();
      }).catch(function(e) {
        document.getElementById("lm_msg").textContent = e.message;
      });
    };
    document.getElementById("lm_verify").onclick = function() {
      var phone = document.getElementById("lm_phone").value.replace(/\D/g,"");
      var code = document.getElementById("lm_otp").value.trim();
      if (code.length < 4) { document.getElementById("lm_msg").textContent = "Enter OTP"; return; }
      document.getElementById("lm_msg").textContent = "Verifying...";
      window.PNW_AUTH.verifyOTP(phone, code).then(function(r) {
        document.getElementById("lm_msg").textContent = "Login successful!";
        setTimeout(function() {
          modal.remove();
          if (typeof window.updateAuthUI === "function") window.updateAuthUI();
          toast("Welcome" + (r.name ? ", " + r.name : "") + "!");
        }, 500);
      }).catch(function(e) {
        document.getElementById("lm_msg").textContent = e.message;
      });
    };
    document.getElementById("lm_back").onclick = function() {
      document.getElementById("lm_step1").style.display = "";
      document.getElementById("lm_step2").style.display = "none";
      document.getElementById("lm_msg").textContent = "";
    };
    document.getElementById("lm_phone").focus();
  }
  window.PNW.showLogin = showLogin;

  /* ---------------- init ---------------- */
  function init() {
    const h = document.getElementById("site-header");
    if (h) h.innerHTML = headerHTML() + drawerHTML();
    const f = document.getElementById("site-footer");
    if (f) f.innerHTML = footerHTML();

    // events
    const cartBtn = document.getElementById("cartBtn");
    if (cartBtn) cartBtn.addEventListener("click", openDrawer);
    const dc = document.getElementById("drawerClose"); if (dc) dc.addEventListener("click", closeDrawer);
    const ov = document.getElementById("drawerOverlay"); if (ov) ov.addEventListener("click", closeDrawer);

    const ham = document.getElementById("hamburger");
    if (ham) ham.addEventListener("click", () => document.getElementById("nav").classList.toggle("open"));

    // mobile accordion menus
    document.querySelectorAll(".js-acc").forEach((el) => {
      el.addEventListener("click", (e) => {
        if (window.innerWidth <= 720) { e.preventDefault(); el.parentElement.classList.toggle("open"); }
      });
    });

    renderCart(); updateCounts();
  }

  // expose so the optional backend layer (api.js) can rebuild the menus
  // after it loads the live, admin-managed catalog
  window.PNW_initChrome = init;

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
