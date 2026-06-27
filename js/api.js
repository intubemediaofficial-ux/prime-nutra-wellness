/* PrimeNutra Wellness — backend integration (progressive enhancement) v2.
 *
 * Covers: live catalog, OTP auth, customer JWT, server-side cart/wishlist sync,
 * checkout, Razorpay, order tracking, combos, account dashboard.
 *
 * Set window.PNW_API_BASE before this script loads to override the API origin.
 */
(function () {
  "use strict";

  var API_BASE = (typeof window.PNW_API_BASE === "string")
    ? window.PNW_API_BASE
    : "";  // same-origin by default (served via FastAPI)

  var CTOKEN_KEY = "pnw_customer_token";
  var CUSTOMER_KEY = "pnw_customer";

  function url(path) { return (API_BASE || "") + path; }

  function authHeaders() {
    var h = { "Accept": "application/json" };
    var t = localStorage.getItem(CTOKEN_KEY);
    if (t) h["Authorization"] = "Bearer " + t;
    return h;
  }

  function getJSON(path) {
    return fetch(url(path), { headers: authHeaders() })
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); });
  }
  function postJSON(path, body) {
    var h = authHeaders();
    h["Content-Type"] = "application/json";
    return fetch(url(path), { method: "POST", headers: h, body: JSON.stringify(body) })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (data) {
          if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
          return data;
        });
      });
  }
  function putJSON(path, body) {
    var h = authHeaders();
    h["Content-Type"] = "application/json";
    return fetch(url(path), { method: "PUT", headers: h, body: JSON.stringify(body) })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (data) {
          if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
          return data;
        });
      });
  }
  function deleteJSON(path) {
    return fetch(url(path), { method: "DELETE", headers: authHeaders() })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (data) {
          if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
          return data;
        });
      });
  }

  function mapProduct(p) {
    return {
      id: p.id, name: p.name, category: p.category_id, concerns: p.concerns || [],
      price: p.price, mrp: p.mrp, rating: p.rating,
      reviews: p.reviews_count || p.reviews || 0,
      emoji: p.emoji || "🌿", badge: p.badge || "",
      sizes: (p.sizes && p.sizes.length) ? p.sizes : ["Default"],
      desc: p.description || "", benefits: p.benefits || [],
      image: p.image || "", gallery: p.gallery || [],
      ingredients: p.ingredients || "", faqs: p.faqs || [],
      specifications: p.specifications || {},
      variants: p.variants || [],
      hsn_code: p.hsn_code || "", gst_rate: p.gst_rate || 18,
      sku: p.sku || "", stock: p.stock, weight_grams: p.weight_grams || 0,
      featured: p.featured, active: p.active,
      seo_title: p.seo_title || "", seo_description: p.seo_description || "",
      video_url: p.video_url || "",
      low_stock_threshold: p.low_stock_threshold || 5,
    };
  }

  function replaceArray(arr, items) {
    if (!Array.isArray(arr) || !Array.isArray(items) || !items.length) return;
    arr.length = 0;
    items.forEach(function (i) { arr.push(i); });
  }

  // ─── Customer Auth ───
  window.PNW_AUTH = {
    token: function () { return localStorage.getItem(CTOKEN_KEY) || ""; },
    customer: function () {
      try { return JSON.parse(localStorage.getItem(CUSTOMER_KEY) || "null"); } catch (e) { return null; }
    },
    isLoggedIn: function () { return !!localStorage.getItem(CTOKEN_KEY); },
    sendOTP: function (phone) { return postJSON("/api/auth/otp/send", { phone: phone }); },
    verifyOTP: function (phone, code) {
      return postJSON("/api/auth/otp/verify", { phone: phone, code: code }).then(function (r) {
        localStorage.setItem(CTOKEN_KEY, r.access_token);
        localStorage.setItem(CUSTOMER_KEY, JSON.stringify({ id: r.customer_id, phone: r.phone, name: r.name }));
        return r;
      });
    },
    getProfile: function () { return getJSON("/api/auth/profile"); },
    updateProfile: function (data) { return putJSON("/api/auth/profile", data); },
    getAddresses: function () { return getJSON("/api/auth/addresses"); },
    addAddress: function (data) { return postJSON("/api/auth/addresses", data); },
    updateAddress: function (id, data) { return putJSON("/api/auth/addresses/" + id, data); },
    deleteAddress: function (id) { return deleteJSON("/api/auth/addresses/" + id); },
    logout: function () {
      localStorage.removeItem(CTOKEN_KEY);
      localStorage.removeItem(CUSTOMER_KEY);
      window.location.reload();
    },
  };

  // ─── Customer Dashboard ───
  window.PNW_ACCOUNT = {
    getOrders: function () { return getJSON("/api/customer/orders"); },
    getOrder: function (id) { return getJSON("/api/customer/orders/" + id); },
    getWishlist: function () { return getJSON("/api/customer/wishlist"); },
    addWishlist: function (pid) { return postJSON("/api/customer/wishlist/" + pid, {}); },
    removeWishlist: function (pid) { return deleteJSON("/api/customer/wishlist/" + pid); },
    getCart: function () { return getJSON("/api/customer/cart"); },
    syncCart: function (items) { return postJSON("/api/customer/cart/sync", { items: items }); },
    getRecentlyViewed: function () { return getJSON("/api/customer/recently-viewed"); },
    trackRecentlyViewed: function (pid) { return postJSON("/api/customer/recently-viewed/" + pid, {}); },
    submitReview: function (data) { return postJSON("/api/customer/reviews", data); },
    requestReturn: function (data) { return postJSON("/api/customer/returns", data); },
    getReturns: function () { return getJSON("/api/customer/returns"); },
  };

  // ─── API ───
  window.PNW_API = {
    base: API_BASE,
    ready: false,
    config: { razorpay_enabled: false, cod_enabled: true },
    payConfig: function () { return getJSON("/api/payments/config"); },
    placeOrder: function (payload) {
      var h = authHeaders();
      h["Content-Type"] = "application/json";
      return fetch(url("/api/orders"), { method: "POST", headers: h, body: JSON.stringify(payload) })
        .then(function (r) {
          return r.json().catch(function () { return {}; }).then(function (data) {
            if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
            return data;
          });
        });
    },
    createRazorpay: function (orderId) { return postJSON("/api/payments/razorpay/create", { order_id: orderId }); },
    verifyRazorpay: function (payload) { return postJSON("/api/payments/razorpay/verify", payload); },
    checkoutQuote: function (payload) { return postJSON("/api/checkout/quote", payload); },
    trackOrder: function (orderId, phone) { return getJSON("/api/orders/" + orderId + "/track?phone=" + phone); },
    getCombos: function (productId) { return getJSON("/api/combos/for-product/" + productId); },
    getCartCombos: function (pids) { return getJSON("/api/combos/for-cart?product_ids=" + pids.join(",")); },
    getProductReviews: function (pid) { return getJSON("/api/products/" + pid + "/reviews"); },
    getPublicSettings: function () { return getJSON("/api/public/settings"); },
    getBlogPosts: function (params) {
      var q = params ? "?" + Object.keys(params).map(function(k){return k+"="+encodeURIComponent(params[k]);}).join("&") : "";
      return getJSON("/api/blog/posts" + q);
    },
    getBlogPost: function (slug) { return getJSON("/api/blog/posts/" + slug); },
  };

  function rerender() {
    try { if (typeof window.PNW_initChrome === "function") window.PNW_initChrome(); } catch (e) {}
    try { if (typeof window.pageRender === "function") window.pageRender(); } catch (e) {}
    try { if (typeof window.updateAuthUI === "function") window.updateAuthUI(); } catch (e) {}
  }

  // Load live catalog + payment config.
  Promise.all([
    getJSON("/api/products"),
    getJSON("/api/categories"),
    getJSON("/api/concerns"),
  ]).then(function (res) {
    var products = res[0], cats = res[1], concerns = res[2];
    if (typeof PRODUCTS !== "undefined") replaceArray(PRODUCTS, (products || []).map(mapProduct));
    if (typeof CATEGORIES !== "undefined") replaceArray(CATEGORIES, cats || []);
    if (typeof CONCERNS !== "undefined") replaceArray(CONCERNS, concerns || []);
    window.PNW_API.ready = true;
    rerender();
  }).catch(function () { /* offline → keep bundled catalog */ });

  window.PNW_API.payConfig().then(function (cfg) {
    window.PNW_API.config = cfg;
    rerender();
  }).catch(function () {});

  // Inject auth UI state
  window.updateAuthUI = function () {
    var loginBtns = document.querySelectorAll(".auth-login-btn, #authLoginBtn");
    var accountBtns = document.querySelectorAll(".auth-account-btn, #authAccountBtn");
    var loggedIn = window.PNW_AUTH.isLoggedIn();
    loginBtns.forEach(function (b) { b.style.display = loggedIn ? "none" : ""; });
    accountBtns.forEach(function (b) { b.style.display = loggedIn ? "" : "none"; });
  };
  setTimeout(function() { if (typeof window.updateAuthUI === "function") window.updateAuthUI(); }, 500);
})();
