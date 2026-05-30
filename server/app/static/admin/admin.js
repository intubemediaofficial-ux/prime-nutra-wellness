/* PrimeNutra Wellness — Admin panel SPA (vanilla JS) */
const TKEY = "pnw_admin_token";
let TOKEN = localStorage.getItem(TKEY) || "";
let CACHE = { categories: [], concerns: [], products: [] };

/* ---------------- API ---------------- */
async function api(path, opts = {}) {
  opts.headers = opts.headers || {};
  if (TOKEN) opts.headers["Authorization"] = "Bearer " + TOKEN;
  if (opts.json !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.json);
    delete opts.json;
  }
  const res = await fetch(path, opts);
  if (res.status === 401) { logout(); throw new Error("Session expired"); }
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch (e) {}
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res;
}

/* ---------------- helpers ---------------- */
const $ = (s, r = document) => r.querySelector(s);
const el = (h) => { const t = document.createElement("template"); t.innerHTML = h.trim(); return t.content.firstElementChild; };
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const rs = (v) => "₹" + Number(v || 0).toLocaleString("en-IN");

let toastT;
function toast(msg, err = false) {
  const t = $("#toast"); t.textContent = msg; t.className = "show" + (err ? " err" : "");
  clearTimeout(toastT); toastT = setTimeout(() => t.className = "", 2600);
}

function closeModal() { $("#modalRoot").innerHTML = ""; }
function modal(title, bodyHtml, footerHtml) {
  const m = el(`<div class="modal-bg"><div class="modal">
    <header><h3>${esc(title)}</h3><button class="x" id="mClose">&times;</button></header>
    <div class="body">${bodyHtml}</div>
    <footer>${footerHtml}</footer></div></div>`);
  m.addEventListener("click", e => { if (e.target === m) closeModal(); });
  $("#mClose", m).onclick = closeModal;
  $("#modalRoot").innerHTML = ""; $("#modalRoot").appendChild(m);
  return m;
}

/* ---------------- auth ---------------- */
$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#lgErr").textContent = "";
  try {
    const r = await api("/api/admin/login", { method: "POST", json: { username: $("#lgUser").value, password: $("#lgPass").value } });
    TOKEN = r.access_token; localStorage.setItem(TKEY, TOKEN);
    $("#whoName").textContent = r.username;
    enterApp();
  } catch (err) { $("#lgErr").textContent = err.message; }
});

function logout() {
  TOKEN = ""; localStorage.removeItem(TKEY);
  $("#app").classList.add("hidden"); $("#login").classList.remove("hidden");
}
$("#logout").onclick = logout;

async function enterApp() {
  $("#login").classList.add("hidden"); $("#app").classList.remove("hidden");
  try {
    const me = await api("/api/admin/me"); $("#whoName").textContent = me.username;
    await loadCatalogMeta();
    go("dashboard");
  } catch (e) { logout(); }
}

async function loadCatalogMeta() {
  CACHE.categories = await api("/api/categories");
  CACHE.concerns = await api("/api/concerns");
}

/* ---------------- router ---------------- */
const TITLES = { dashboard: "Dashboard", products: "Products", orders: "Orders", categories: "Categories", concerns: "Health Concerns", import: "Import / Export", coupons: "Coupons", settings: "Settings", account: "Change Password" };
$("#nav").addEventListener("click", e => {
  const a = e.target.closest("a[data-view]"); if (!a) return;
  go(a.dataset.view);
});
function go(view) {
  document.querySelectorAll("#nav a").forEach(a => a.classList.toggle("active", a.dataset.view === view));
  $("#viewTitle").textContent = TITLES[view] || view;
  (VIEWS[view] || VIEWS.dashboard)();
}

/* ================= VIEWS ================= */
const VIEWS = {};

/* ---- Dashboard ---- */
VIEWS.dashboard = async () => {
  const v = $("#view"); v.innerHTML = `<div class="muted">Loading…</div>`;
  try {
    const s = await api("/api/admin/stats");
    const sx = s.by_status || {};
    v.innerHTML = `
    <div class="cards">
      <div class="card"><div class="k">Total Orders</div><div class="v">${s.orders}</div></div>
      <div class="card"><div class="k">Revenue</div><div class="v">${rs(s.revenue)}</div></div>
      <div class="card"><div class="k">Products</div><div class="v">${s.products}</div></div>
      <div class="card"><div class="k">Low Stock (≤5)</div><div class="v">${s.low_stock}</div></div>
    </div>
    <div class="panel"><h3>Orders by status</h3>
      <div class="chips">
        ${["placed","confirmed","shipped","delivered","cancelled"].map(st => `<span class="chip">${st}: <b>${sx[st]||0}</b></span>`).join("")}
      </div>
    </div>
    <div class="panel"><h3>Quick actions</h3>
      <div class="toolbar">
        <button class="btn" onclick="go('products')">+ Manage products</button>
        <button class="btn ghost" onclick="go('orders')">View orders</button>
        <button class="btn ghost" onclick="go('import')">Bulk import (Excel)</button>
        <button class="btn ghost" onclick="go('settings')">Razorpay / Settings</button>
      </div>
    </div>`;
  } catch (e) { v.innerHTML = `<div class="panel">Error: ${esc(e.message)}</div>`; }
};

/* ---- Products ---- */
VIEWS.products = async () => {
  const v = $("#view");
  v.innerHTML = `<div class="panel">
    <div class="toolbar">
      <input id="pSearch" class="grow" placeholder="Search products…">
      <select id="pCat"><option value="">All categories</option>${CACHE.categories.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join("")}</select>
      <button class="btn" id="pAdd">+ Add product</button>
    </div>
    <div id="pTable" class="muted">Loading…</div>
  </div>`;
  $("#pAdd").onclick = () => productModal();
  const render = async () => {
    const list = await api("/api/products?include_inactive=true");
    CACHE.products = list;
    const term = $("#pSearch").value.toLowerCase(), cat = $("#pCat").value;
    const rows = list.filter(p => (!cat || p.category_id === cat) && (!term || p.name.toLowerCase().includes(term)));
    $("#pTable").innerHTML = `<table><thead><tr><th></th><th>Name</th><th>Category</th><th>Price</th><th>MRP</th><th>Stock</th><th>Status</th><th></th></tr></thead>
      <tbody>${rows.map(p => `<tr>
        <td>${p.image ? `<img class="thumb" src="${esc(p.image)}">` : `<span class="thumb">${p.emoji||"🌿"}</span>`}</td>
        <td><b>${esc(p.name)}</b><br><span class="muted" style="font-size:11px">${esc(p.id)}</span></td>
        <td>${esc((CACHE.categories.find(c=>c.id===p.category_id)||{}).name||p.category_id||"-")}</td>
        <td>${rs(p.price)}</td><td class="muted">${rs(p.mrp)}</td>
        <td>${p.stock}</td>
        <td>${p.active ? '<span class="pill green">Active</span>' : '<span class="pill gray">Hidden</span>'}</td>
        <td><div class="row-actions">
          <button class="btn sm ghost" data-edit="${esc(p.id)}">Edit</button>
          <button class="btn sm red" data-del="${esc(p.id)}">Del</button>
        </div></td></tr>`).join("")}</tbody></table>
      <p class="muted" style="margin-top:10px">${rows.length} product(s)</p>`;
    $("#pTable").querySelectorAll("[data-edit]").forEach(b => b.onclick = () => productModal(list.find(x => x.id === b.dataset.edit)));
    $("#pTable").querySelectorAll("[data-del]").forEach(b => b.onclick = () => delProduct(b.dataset.del));
  };
  $("#pSearch").oninput = render; $("#pCat").onchange = render;
  render();
};

function productModal(p) {
  const isEdit = !!p; p = p || {};
  const catOpts = CACHE.categories.map(c => `<option value="${c.id}" ${p.category_id===c.id?"selected":""}>${esc(c.name)}</option>`).join("");
  const concernChips = CACHE.concerns.map(c => `<label class="chip"><input type="checkbox" value="${c.id}" ${(p.concerns||[]).includes(c.id)?"checked":""}> ${esc(c.name)}</label>`).join("");
  const m = modal(isEdit ? "Edit product" : "Add product", `
    <div class="grid2">
      <div class="field"><label>Name *</label><input id="f_name" value="${esc(p.name||"")}"></div>
      <div class="field"><label>Category *</label><select id="f_cat"><option value="">Select…</option>${catOpts}</select></div>
    </div>
    <div class="grid3">
      <div class="field"><label>Price (₹) *</label><input id="f_price" type="number" value="${p.price??""}"></div>
      <div class="field"><label>MRP (₹)</label><input id="f_mrp" type="number" value="${p.mrp??""}"></div>
      <div class="field"><label>Stock</label><input id="f_stock" type="number" value="${p.stock??100}"></div>
    </div>
    <div class="grid3">
      <div class="field"><label>Rating</label><input id="f_rating" type="number" step="0.1" value="${p.rating??4.5}"></div>
      <div class="field"><label>Reviews</label><input id="f_reviews" type="number" value="${p.reviews??0}"></div>
      <div class="field"><label>Emoji</label><input id="f_emoji" value="${esc(p.emoji||"🌿")}"></div>
    </div>
    <div class="grid2">
      <div class="field"><label>Badge (e.g. Bestseller, 20% OFF)</label><input id="f_badge" value="${esc(p.badge||"")}"></div>
      <div class="field"><label>Sizes (comma separated)</label><input id="f_sizes" value="${esc((p.sizes||[]).join(", "))}"></div>
    </div>
    <div class="field"><label>Health concerns</label><div class="chips" id="f_concerns">${concernChips}</div></div>
    <div class="field"><label>Description</label><textarea id="f_desc" rows="3">${esc(p.description||"")}</textarea></div>
    <div class="field"><label>Benefits (one per line)</label><textarea id="f_benefits" rows="3">${esc((p.benefits||[]).join("\n"))}</textarea></div>
    <div class="field"><label>Product image</label>
      <div class="toolbar">
        <img class="imgprev" id="f_imgprev" src="${esc(p.image||"")}" style="${p.image?"":"display:none"}">
        <input type="file" id="f_file" accept="image/*" style="width:auto">
        <input id="f_image" placeholder="/uploads/… or full URL" value="${esc(p.image||"")}">
      </div>
    </div>
    <label class="chip" style="display:inline-flex"><input type="checkbox" id="f_active" ${p.active!==false?"checked":""}> Active (visible on store)</label>
  `, `<button class="btn gray" id="mCancel">Cancel</button><button class="btn" id="mSave">${isEdit?"Save changes":"Create product"}</button>`);

  $("#mCancel", m).onclick = closeModal;
  $("#f_file", m).onchange = async (e) => {
    const file = e.target.files[0]; if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    try { const r = await api("/api/admin/upload", { method: "POST", body: fd }); $("#f_image", m).value = r.url; const pv = $("#f_imgprev", m); pv.src = r.url; pv.style.display = ""; toast("Image uploaded"); }
    catch (err) { toast(err.message, true); }
  };
  $("#mSave", m).onclick = async () => {
    const payload = {
      id: isEdit ? p.id : undefined,
      name: $("#f_name", m).value.trim(),
      category_id: $("#f_cat", m).value,
      price: parseFloat($("#f_price", m).value) || 0,
      mrp: parseFloat($("#f_mrp", m).value) || 0,
      stock: parseInt($("#f_stock", m).value) || 0,
      rating: parseFloat($("#f_rating", m).value) || 4.5,
      reviews: parseInt($("#f_reviews", m).value) || 0,
      emoji: $("#f_emoji", m).value || "🌿",
      badge: $("#f_badge", m).value.trim(),
      sizes: $("#f_sizes", m).value.split(",").map(s => s.trim()).filter(Boolean),
      concerns: [...m.querySelectorAll("#f_concerns input:checked")].map(c => c.value),
      description: $("#f_desc", m).value.trim(),
      benefits: $("#f_benefits", m).value.split("\n").map(s => s.trim()).filter(Boolean),
      image: $("#f_image", m).value.trim(),
      active: $("#f_active", m).checked,
    };
    if (!payload.name || !payload.category_id) { toast("Name and category are required", true); return; }
    try {
      if (isEdit) await api("/api/admin/products/" + encodeURIComponent(p.id), { method: "PUT", json: payload });
      else await api("/api/admin/products", { method: "POST", json: payload });
      toast("Saved"); closeModal(); VIEWS.products();
    } catch (err) { toast(err.message, true); }
  };
}

async function delProduct(id) {
  if (!confirm("Delete this product permanently?")) return;
  try { await api("/api/admin/products/" + encodeURIComponent(id), { method: "DELETE" }); toast("Deleted"); VIEWS.products(); }
  catch (e) { toast(e.message, true); }
}

/* ---- Orders ---- */
VIEWS.orders = async () => {
  const v = $("#view");
  v.innerHTML = `<div class="panel">
    <div class="toolbar">
      <select id="oStatus"><option value="">All statuses</option>${["placed","confirmed","shipped","delivered","cancelled"].map(s=>`<option>${s}</option>`).join("")}</select>
      <button class="btn ghost" id="oReload">↻ Refresh</button>
    </div>
    <div id="oTable" class="muted">Loading…</div></div>`;
  const render = async () => {
    const st = $("#oStatus").value;
    const list = await api("/api/admin/orders" + (st ? "?status=" + st : ""));
    $("#oTable").innerHTML = `<table><thead><tr><th>Order</th><th>Customer</th><th>Items</th><th>Total</th><th>Payment</th><th>Status</th><th></th></tr></thead>
      <tbody>${list.map(o => `<tr>
        <td><b>${esc(o.id)}</b><br><span class="muted" style="font-size:11px">${new Date(o.created_at).toLocaleString("en-IN")}</span></td>
        <td>${esc(o.customer_name)}<br><span class="muted">${esc(o.phone)}</span></td>
        <td>${o.items.length}</td>
        <td>${rs(o.total)}</td>
        <td>${esc(o.payment_method)} <span class="pill ${o.payment_status==='paid'?'green':o.payment_status==='failed'?'red':'amber'}">${o.payment_status}</span></td>
        <td>${statusPill(o.status)}</td>
        <td><button class="btn sm ghost" data-view-o="${esc(o.id)}">View</button></td></tr>`).join("")}</tbody></table>
      <p class="muted" style="margin-top:10px">${list.length} order(s)</p>`;
    $("#oTable").querySelectorAll("[data-view-o]").forEach(b => b.onclick = () => orderModal(list.find(o => o.id === b.dataset.viewO)));
  };
  $("#oStatus").onchange = render; $("#oReload").onclick = render;
  render();
};
const statusPill = (s) => `<span class="pill ${({placed:'amber',confirmed:'green',shipped:'green',delivered:'green',cancelled:'red'})[s]||'gray'}">${s}</span>`;

function orderModal(o) {
  const items = o.items.map(i => `<tr><td>${esc(i.name)}</td><td>${esc(i.size||"-")}</td><td>${i.qty}</td><td>${rs(i.price)}</td><td>${rs(i.price*i.qty)}</td></tr>`).join("");
  const opts = ["placed","confirmed","shipped","delivered","cancelled"].map(s => `<option ${o.status===s?"selected":""}>${s}</option>`).join("");
  const m = modal("Order " + o.id, `
    <div class="grid2">
      <div><h3>Customer</h3>
        <p>${esc(o.customer_name)}<br>${esc(o.phone)}<br>${esc(o.email||"")}</p>
        <p class="muted">${esc(o.address)}, ${esc(o.city)}, ${esc(o.state)} - ${esc(o.pincode)}<br>${esc(o.landmark||"")}</p>
      </div>
      <div><h3>Payment</h3>
        <p>Method: <b>${esc(o.payment_method)}</b><br>Status: ${esc(o.payment_status)}<br>${o.coupon_code?("Coupon: "+esc(o.coupon_code)):""}</p>
        <p class="muted">${o.razorpay_order_id?("RZP: "+esc(o.razorpay_order_id)):""}</p>
      </div>
    </div>
    <h3>Items</h3>
    <table><thead><tr><th>Product</th><th>Size</th><th>Qty</th><th>Price</th><th>Total</th></tr></thead><tbody>${items}</tbody></table>
    <p style="text-align:right;margin-top:12px">Subtotal: ${rs(o.subtotal)} &nbsp; Discount: −${rs(o.discount)} &nbsp; Shipping: ${rs(o.shipping)}<br><b style="font-size:18px">Total: ${rs(o.total)}</b></p>
    <div class="field" style="margin-top:14px"><label>Update status</label><select id="o_status">${opts}</select></div>
  `, `<button class="btn gray" id="mCancel">Close</button><button class="btn" id="mSave">Save status</button>`);
  $("#mCancel", m).onclick = closeModal;
  $("#mSave", m).onclick = async () => {
    try { await api(`/api/admin/orders/${o.id}/status`, { method: "PUT", json: { status: $("#o_status", m).value } }); toast("Status updated"); closeModal(); VIEWS.orders(); }
    catch (e) { toast(e.message, true); }
  };
}

/* ---- Categories & Concerns (shared) ---- */
function taxonomyView(kind, apiList, apiSave, apiDel, label) {
  return async () => {
    const v = $("#view");
    const list = await api(apiList);
    CACHE[kind] = list;
    v.innerHTML = `<div class="panel">
      <div class="toolbar"><button class="btn" id="tAdd">+ Add ${label}</button></div>
      <table><thead><tr><th></th><th>Name</th><th>ID</th><th>Blurb</th><th></th></tr></thead>
      <tbody>${list.map(c => `<tr><td style="font-size:20px">${c.emoji||""}</td><td><b>${esc(c.name)}</b></td><td class="muted">${esc(c.id)}</td><td>${esc(c.blurb||"")}</td>
        <td><div class="row-actions"><button class="btn sm ghost" data-e="${esc(c.id)}">Edit</button><button class="btn sm red" data-d="${esc(c.id)}">Del</button></div></td></tr>`).join("")}</tbody></table></div>`;
    const open = (c) => {
      c = c || {};
      const m = modal((c.id?"Edit ":"Add ")+label, `
        <div class="grid2"><div class="field"><label>Name *</label><input id="t_name" value="${esc(c.name||"")}"></div>
        <div class="field"><label>Emoji</label><input id="t_emoji" value="${esc(c.emoji||"")}"></div></div>
        <div class="field"><label>ID / slug ${c.id?"(locked)":"(optional)"}</label><input id="t_id" value="${esc(c.id||"")}" ${c.id?"disabled":""}></div>
        <div class="field"><label>Blurb</label><input id="t_blurb" value="${esc(c.blurb||"")}"></div>`,
        `<button class="btn gray" id="mCancel">Cancel</button><button class="btn" id="mSave">Save</button>`);
      $("#mCancel", m).onclick = closeModal;
      $("#mSave", m).onclick = async () => {
        const payload = { id: c.id || $("#t_id", m).value.trim(), name: $("#t_name", m).value.trim(), emoji: $("#t_emoji", m).value.trim(), blurb: $("#t_blurb", m).value.trim() };
        if (!payload.name) { toast("Name required", true); return; }
        try { await api(apiSave, { method: "POST", json: payload }); toast("Saved"); closeModal(); go(kind); await loadCatalogMeta(); }
        catch (e) { toast(e.message, true); }
      };
    };
    $("#tAdd").onclick = () => open();
    v.querySelectorAll("[data-e]").forEach(b => b.onclick = () => open(list.find(x => x.id === b.dataset.e)));
    v.querySelectorAll("[data-d]").forEach(b => b.onclick = async () => {
      if (!confirm("Delete " + label + "?")) return;
      try { await api(apiDel + encodeURIComponent(b.dataset.d), { method: "DELETE" }); toast("Deleted"); go(kind); await loadCatalogMeta(); }
      catch (e) { toast(e.message, true); }
    });
  };
}
VIEWS.categories = taxonomyView("categories", "/api/categories", "/api/admin/categories", "/api/admin/categories/", "category");
VIEWS.concerns = taxonomyView("concerns", "/api/concerns", "/api/admin/concerns", "/api/admin/concerns/", "concern");

/* ---- Import / Export ---- */
VIEWS.import = async () => {
  const v = $("#view");
  v.innerHTML = `<div class="panel"><h3>Export</h3>
    <p class="muted">Download all products as Excel, edit them, then re-upload to bulk update.</p>
    <div class="toolbar">
      <button class="btn ghost" id="dlTemplate">⬇ Download template</button>
      <button class="btn" id="dlExport">⬇ Export all products (.xlsx)</button>
    </div></div>
    <div class="panel"><h3>Import (Excel / CSV)</h3>
    <p class="muted">Columns: id, name, category_id, concerns, price, mrp, rating, reviews, emoji, badge, image, description, benefits, sizes, stock, active. Existing rows (matched by <b>id</b>) are updated, new ids are created.</p>
    <div class="toolbar"><input type="file" id="impFile" accept=".xlsx,.csv" style="width:auto"><button class="btn" id="impBtn">Upload &amp; import</button></div>
    <div id="impResult"></div></div>`;
  const dl = async (url, name) => {
    try { const res = await api(url); const blob = await res.blob(); const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; a.click(); }
    catch (e) { toast(e.message, true); }
  };
  $("#dlTemplate").onclick = () => dl("/api/admin/products/template.xlsx", "primenutra-template.xlsx");
  $("#dlExport").onclick = () => dl("/api/admin/products/export.xlsx", "primenutra-products.xlsx");
  $("#impBtn").onclick = async () => {
    const f = $("#impFile").files[0]; if (!f) { toast("Choose a file first", true); return; }
    const fd = new FormData(); fd.append("file", f);
    $("#impResult").innerHTML = `<p class="muted">Importing…</p>`;
    try {
      const r = await api("/api/admin/products/import", { method: "POST", body: fd });
      $("#impResult").innerHTML = `<div class="panel" style="margin-top:14px"><b style="color:var(--green-700)">✓ ${r.created} created, ${r.updated} updated.</b>
        ${r.errors.length ? `<ul style="color:var(--red)">${r.errors.map(e=>`<li>${esc(e)}</li>`).join("")}</ul>` : ""}</div>`;
      toast("Import complete");
    } catch (e) { $("#impResult").innerHTML = ""; toast(e.message, true); }
  };
};

/* ---- Coupons ---- */
VIEWS.coupons = async () => {
  const v = $("#view");
  const list = await api("/api/admin/coupons");
  v.innerHTML = `<div class="panel"><div class="toolbar"><button class="btn" id="cAdd">+ Add coupon</button></div>
    <table><thead><tr><th>Code</th><th>Type</th><th>Value</th><th>Min order</th><th>Active</th><th></th></tr></thead>
    <tbody>${list.map(c => `<tr><td><b>${esc(c.code)}</b></td><td>${esc(c.type)}</td><td>${c.type==="percent"?c.value+"%":rs(c.value)}</td><td>${rs(c.min_order)}</td>
      <td>${c.active?'<span class="pill green">Yes</span>':'<span class="pill gray">No</span>'}</td>
      <td><div class="row-actions"><button class="btn sm ghost" data-e='${esc(JSON.stringify(c))}'>Edit</button><button class="btn sm red" data-d="${esc(c.code)}">Del</button></div></td></tr>`).join("")}</tbody></table></div>`;
  const open = (c) => {
    c = c || { type: "percent", active: true };
    const m = modal((c.code?"Edit ":"Add ")+"coupon", `
      <div class="grid2"><div class="field"><label>Code *</label><input id="c_code" value="${esc(c.code||"")}" ${c.code?"disabled":""}></div>
      <div class="field"><label>Type</label><select id="c_type"><option value="percent" ${c.type==="percent"?"selected":""}>Percent (%)</option><option value="flat" ${c.type==="flat"?"selected":""}>Flat (₹)</option></select></div></div>
      <div class="grid2"><div class="field"><label>Value</label><input id="c_value" type="number" value="${c.value??0}"></div>
      <div class="field"><label>Min order (₹)</label><input id="c_min" type="number" value="${c.min_order??0}"></div></div>
      <label class="chip" style="display:inline-flex"><input type="checkbox" id="c_active" ${c.active!==false?"checked":""}> Active</label>`,
      `<button class="btn gray" id="mCancel">Cancel</button><button class="btn" id="mSave">Save</button>`);
    $("#mCancel", m).onclick = closeModal;
    $("#mSave", m).onclick = async () => {
      const payload = { code: c.code || $("#c_code", m).value, type: $("#c_type", m).value, value: parseFloat($("#c_value", m).value)||0, min_order: parseFloat($("#c_min", m).value)||0, active: $("#c_active", m).checked };
      if (!payload.code) { toast("Code required", true); return; }
      try { await api("/api/admin/coupons", { method: "POST", json: payload }); toast("Saved"); closeModal(); VIEWS.coupons(); }
      catch (e) { toast(e.message, true); }
    };
  };
  $("#cAdd").onclick = () => open();
  v.querySelectorAll("[data-e]").forEach(b => b.onclick = () => open(JSON.parse(b.dataset.e)));
  v.querySelectorAll("[data-d]").forEach(b => b.onclick = async () => { if (!confirm("Delete coupon?")) return; await api("/api/admin/coupons/" + encodeURIComponent(b.dataset.d), { method: "DELETE" }); toast("Deleted"); VIEWS.coupons(); });
};

/* ---- Settings ---- */
VIEWS.settings = async () => {
  const v = $("#view");
  const s = await api("/api/admin/settings");
  const chk = (k) => s[k] === "true" ? "checked" : "";
  v.innerHTML = `
  <div class="panel"><h3>Store</h3>
    <div class="grid2">
      <div class="field"><label>Store name</label><input id="s_store_name" value="${esc(s.store_name||"")}"></div>
      <div class="field"><label>WhatsApp number (with country code)</label><input id="s_whatsapp_number" value="${esc(s.whatsapp_number||"")}"></div>
    </div>
    <div class="grid2">
      <div class="field"><label>Support email</label><input id="s_support_email" value="${esc(s.support_email||"")}"></div>
      <div class="field"><label>Free shipping threshold (₹, 0 = always free)</label><input id="s_free_ship_threshold" type="number" value="${esc(s.free_ship_threshold||"0")}"></div>
    </div>
    <div class="field" style="max-width:240px"><label>Shipping fee (₹, 0 = free)</label><input id="s_shipping_fee" type="number" value="${esc(s.shipping_fee||"0")}"></div>
  </div>
  <div class="panel"><h3>Payments</h3>
    <label class="chip" style="display:inline-flex;margin-bottom:12px"><input type="checkbox" id="s_cod_enabled" ${chk("cod_enabled")}> Cash on Delivery enabled</label><br>
    <label class="chip" style="display:inline-flex;margin-bottom:12px"><input type="checkbox" id="s_razorpay_enabled" ${chk("razorpay_enabled")}> Razorpay enabled</label>
    <div class="grid2">
      <div class="field"><label>Razorpay Key ID</label><input id="s_razorpay_key_id" value="${esc(s.razorpay_key_id||"")}" placeholder="rzp_live_…"></div>
      <div class="field"><label>Razorpay Key Secret ${s.razorpay_key_secret_set?"<span class='pill green'>set</span>":"<span class='pill gray'>not set</span>"}</label><input id="s_razorpay_key_secret" type="password" placeholder="${s.razorpay_key_secret_set?'•••••• (leave blank to keep)':'enter secret'}"></div>
    </div>
    <p class="help">Get keys at dashboard.razorpay.com → Settings → API Keys. Use test keys (rzp_test_…) while testing.</p>
  </div>
  <div class="panel"><h3>Email (Brevo)</h3>
    <div class="grid2">
      <div class="field"><label>From name</label><input id="s_brevo_from_name" value="${esc(s.brevo_from_name||"")}"></div>
      <div class="field"><label>From email</label><input id="s_brevo_from_email" value="${esc(s.brevo_from_email||"")}"></div>
    </div>
    <div class="field"><label>Brevo API key ${s.brevo_api_key?"":"<span class='muted'>(uses server BREVO_API_KEY if blank)</span>"}</label><input id="s_brevo_api_key" value="${esc(s.brevo_api_key||"")}" placeholder="xkeysib-…"></div>
  </div>
  <button class="btn" id="sSave">Save all settings</button>`;
  $("#sSave").onclick = async () => {
    const keys = ["store_name","whatsapp_number","support_email","free_ship_threshold","shipping_fee","razorpay_key_id","razorpay_key_secret","brevo_from_name","brevo_from_email","brevo_api_key"];
    const values = {};
    keys.forEach(k => values[k] = $("#s_" + k).value);
    values.cod_enabled = $("#s_cod_enabled").checked ? "true" : "false";
    values.razorpay_enabled = $("#s_razorpay_enabled").checked ? "true" : "false";
    try { await api("/api/admin/settings", { method: "PUT", json: { values } }); toast("Settings saved"); VIEWS.settings(); }
    catch (e) { toast(e.message, true); }
  };
};

/* ---- Account ---- */
VIEWS.account = async () => {
  const v = $("#view");
  v.innerHTML = `<div class="panel" style="max-width:420px"><h3>Change password</h3>
    <div class="field"><label>Current password</label><input id="a_old" type="password"></div>
    <div class="field"><label>New password (min 6 chars)</label><input id="a_new" type="password"></div>
    <button class="btn" id="aSave">Update password</button></div>`;
  $("#aSave").onclick = async () => {
    try { await api("/api/admin/change-password", { method: "POST", json: { old_password: $("#a_old").value, new_password: $("#a_new").value } }); toast("Password updated"); $("#a_old").value=""; $("#a_new").value=""; }
    catch (e) { toast(e.message, true); }
  };
};

/* ---------------- boot ---------------- */
if (TOKEN) enterApp(); else { $("#login").classList.remove("hidden"); }
