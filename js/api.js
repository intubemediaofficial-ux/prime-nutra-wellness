/* PrimeNutra Wellness — backend integration (progressive enhancement).
 *
 * If the backend API is reachable it replaces the bundled catalog with the
 * live, admin-managed data and routes checkout through the API (COD + Razorpay).
 * If the backend is unreachable the site silently falls back to the bundled
 * catalog (js/products.js) and the WhatsApp/localStorage checkout, so the
 * storefront always works even when the API is down.
 *
 * Set window.PNW_API_BASE before this script loads to override the API origin.
 */
(function () {
  "use strict";

  // Default backend origin (Fly.io). Same-origin "" is used automatically when
  // the storefront is served by the FastAPI app itself.
  var API_BASE = (typeof window.PNW_API_BASE === "string")
    ? window.PNW_API_BASE
    : "https://prime-nutra-backend.fly.dev";

  function url(path) { return (API_BASE || "") + path; }

  function getJSON(path) {
    return fetch(url(path), { headers: { "Accept": "application/json" } })
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); });
  }
  function postJSON(path, body) {
    return fetch(url(path), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
        return data;
      });
    });
  }

  // Map an API product to the shape the storefront expects.
  function mapProduct(p) {
    return {
      id: p.id, name: p.name, category: p.category_id, concerns: p.concerns || [],
      price: p.price, mrp: p.mrp, rating: p.rating, reviews: p.reviews,
      emoji: p.emoji || "🌿", badge: p.badge || "", sizes: (p.sizes && p.sizes.length) ? p.sizes : ["Default"],
      desc: p.description || "", benefits: p.benefits || [], image: p.image || "",
    };
  }

  function replaceArray(arr, items) {
    if (!Array.isArray(arr) || !Array.isArray(items) || !items.length) return;
    arr.length = 0;
    items.forEach(function (i) { arr.push(i); });
  }

  // Public API for checkout / payments.
  window.PNW_API = {
    base: API_BASE,
    ready: false,
    config: { razorpay_enabled: false, cod_enabled: true },
    payConfig: function () { return getJSON("/api/payments/config"); },
    placeOrder: function (payload) { return postJSON("/api/orders", payload); },
    createRazorpay: function (orderId) { return postJSON("/api/payments/razorpay/create", { order_id: orderId }); },
    verifyRazorpay: function (payload) { return postJSON("/api/payments/razorpay/verify", payload); },
  };

  function rerender() {
    try { if (typeof window.PNW_initChrome === "function") window.PNW_initChrome(); } catch (e) {}
    try { if (typeof window.pageRender === "function") window.pageRender(); } catch (e) {}
  }

  // Load live catalog + payment config, then refresh the page.
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
})();
