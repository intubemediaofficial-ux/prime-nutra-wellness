/* PrimeNutra Wellness — Admin panel SPA (vanilla JS) — v2 full D2C */
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
const TITLES = {
  dashboard: "Dashboard", products: "Products", orders: "Orders", customers: "Customers",
  categories: "Categories", concerns: "Health Concerns", combos: "Combos", import: "Import / Export",
  coupons: "Coupons", reviews: "Reviews", returns: "Returns & Refunds", inventory: "Inventory",
  influencers: "Influencers", blog: "Blog", reports: "Reports", notifications: "Notifications",
  settings: "Settings", seo: "SEO & Redirects", account: "Change Password",
};
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
      <div class="card"><div class="k">Low Stock</div><div class="v">${s.low_stock}</div></div>
      <div class="card"><div class="k">Customers</div><div class="v">${s.customers}</div></div>
      <div class="card"><div class="k">Pending Returns</div><div class="v">${s.returns}</div></div>
    </div>
    <div class="panel"><h3>Orders by status</h3>
      <div class="chips">
        ${["placed","confirmed","packed","shipped","in_transit","out_for_delivery","delivered","cancelled","returned","refunded"].map(st => `<span class="chip">${st}: <b>${sx[st]||0}</b></span>`).join("")}
      </div>
    </div>
    <div class="panel"><h3>Quick actions</h3>
      <div class="toolbar">
        <button class="btn" onclick="go('products')">Manage products</button>
        <button class="btn ghost" onclick="go('orders')">View orders</button>
        <button class="btn ghost" onclick="go('customers')">Customers</button>
        <button class="btn ghost" onclick="go('reports')">Reports</button>
        <button class="btn ghost" onclick="go('settings')">Settings</button>
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
        <td>${p.stock}${p.stock<=p.low_stock_threshold?' <span class="pill red">Low</span>':''}</td>
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
      <div class="field"><label>SKU</label><input id="f_sku" value="${esc(p.sku||"")}"></div>
      <div class="field"><label>HSN Code</label><input id="f_hsn" value="${esc(p.hsn_code||"")}"></div>
      <div class="field"><label>GST Rate (%)</label><input id="f_gst" type="number" value="${p.gst_rate??18}"></div>
    </div>
    <div class="grid3">
      <div class="field"><label>Rating</label><input id="f_rating" type="number" step="0.1" value="${p.rating??4.5}"></div>
      <div class="field"><label>Emoji</label><input id="f_emoji" value="${esc(p.emoji||"🌿")}"></div>
      <div class="field"><label>Weight (grams)</label><input id="f_weight" type="number" value="${p.weight_grams??0}"></div>
    </div>
    <div class="grid2">
      <div class="field"><label>Badge</label><input id="f_badge" value="${esc(p.badge||"")}"></div>
      <div class="field"><label>Sizes (comma separated)</label><input id="f_sizes" value="${esc((p.sizes||[]).join(", "))}"></div>
    </div>
    <div class="field"><label>Health concerns</label><div class="chips" id="f_concerns">${concernChips}</div></div>
    <div class="field"><label>Description</label><textarea id="f_desc" rows="3">${esc(p.description||"")}</textarea></div>
    <div class="field"><label>Benefits (one per line)</label><textarea id="f_benefits" rows="3">${esc((p.benefits||[]).join("\n"))}</textarea></div>
    <div class="field"><label>Ingredients</label><textarea id="f_ingredients" rows="2">${esc(p.ingredients||"")}</textarea></div>
    <div class="field"><label>Product image</label>
      <div class="toolbar">
        <img class="imgprev" id="f_imgprev" src="${esc(p.image||"")}" style="${p.image?"":"display:none"}">
        <input type="file" id="f_file" accept="image/*" style="width:auto">
        <input id="f_image" placeholder="/uploads/… or full URL" value="${esc(p.image||"")}">
      </div>
    </div>
    <div class="field"><label>Video URL (YouTube)</label><input id="f_video" value="${esc(p.video_url||"")}"></div>
    <div class="grid2">
      <div class="field"><label>SEO Title</label><input id="f_seo_title" value="${esc(p.seo_title||"")}"></div>
      <div class="field"><label>SEO Description</label><input id="f_seo_desc" value="${esc(p.seo_description||"")}"></div>
    </div>
    <div class="chips">
      <label class="chip"><input type="checkbox" id="f_active" ${p.active!==false?"checked":""}> Active</label>
      <label class="chip"><input type="checkbox" id="f_featured" ${p.featured?"checked":""}> Featured</label>
    </div>
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
      sku: $("#f_sku", m).value.trim(),
      hsn_code: $("#f_hsn", m).value.trim(),
      gst_rate: parseFloat($("#f_gst", m).value) || 18,
      rating: parseFloat($("#f_rating", m).value) || 4.5,
      emoji: $("#f_emoji", m).value || "🌿",
      badge: $("#f_badge", m).value.trim(),
      sizes: $("#f_sizes", m).value.split(",").map(s => s.trim()).filter(Boolean),
      concerns: [...m.querySelectorAll("#f_concerns input:checked")].map(c => c.value),
      description: $("#f_desc", m).value.trim(),
      benefits: $("#f_benefits", m).value.split("\n").map(s => s.trim()).filter(Boolean),
      ingredients: $("#f_ingredients", m).value.trim(),
      image: $("#f_image", m).value.trim(),
      video_url: $("#f_video", m).value.trim(),
      weight_grams: parseFloat($("#f_weight", m).value) || 0,
      seo_title: $("#f_seo_title", m).value.trim(),
      seo_description: $("#f_seo_desc", m).value.trim(),
      active: $("#f_active", m).checked,
      featured: $("#f_featured", m).checked,
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
  const allStatuses = ["placed","confirmed","packed","shipped","in_transit","out_for_delivery","delivered","cancelled","returned","refunded"];
  v.innerHTML = `<div class="panel">
    <div class="toolbar">
      <input id="oSearch" class="grow" placeholder="Search order/customer…">
      <select id="oStatus"><option value="">All statuses</option>${allStatuses.map(s=>`<option>${s}</option>`).join("")}</select>
      <button class="btn ghost" id="oReload">Refresh</button>
    </div>
    <div id="oTable" class="muted">Loading…</div></div>`;
  const render = async () => {
    const st = $("#oStatus").value;
    const search = $("#oSearch").value;
    let url = "/api/admin/orders";
    const params = [];
    if (st) params.push("status=" + st);
    if (search) params.push("search=" + encodeURIComponent(search));
    if (params.length) url += "?" + params.join("&");
    const list = await api(url);
    $("#oTable").innerHTML = `<table><thead><tr><th>Order</th><th>Customer</th><th>Items</th><th>Total</th><th>Payment</th><th>Status</th><th></th></tr></thead>
      <tbody>${list.map(o => `<tr>
        <td><b>${esc(o.id)}</b><br><span class="muted" style="font-size:11px">${new Date(o.created_at).toLocaleString("en-IN")}</span></td>
        <td>${esc(o.customer_name)}<br><span class="muted">${esc(o.phone)}</span></td>
        <td>${o.items.length}</td>
        <td>${rs(o.total)}</td>
        <td>${esc(o.payment_method)} <span class="pill ${o.payment_status==='paid'?'green':o.payment_status==='failed'?'red':'amber'}">${o.payment_status}</span></td>
        <td>${statusPill(o.status)}</td>
        <td><div class="row-actions">
          <button class="btn sm ghost" data-view-o="${esc(o.id)}">View</button>
          <a class="btn sm ghost" href="/api/admin/orders/${esc(o.id)}/invoice" target="_blank">Invoice</a>
        </div></td></tr>`).join("")}</tbody></table>
      <p class="muted" style="margin-top:10px">${list.length} order(s)</p>`;
    $("#oTable").querySelectorAll("[data-view-o]").forEach(b => b.onclick = () => orderModal(list.find(o => o.id === b.dataset.viewO)));
  };
  $("#oStatus").onchange = render; $("#oReload").onclick = render; $("#oSearch").oninput = render;
  render();
};
const statusPill = (s) => `<span class="pill ${({placed:'amber',confirmed:'green',packed:'green',shipped:'green',in_transit:'green',out_for_delivery:'green',delivered:'green',cancelled:'red',returned:'amber',refunded:'amber'})[s]||'gray'}">${s}</span>`;

function orderModal(o) {
  const allStatuses = ["placed","confirmed","packed","shipped","in_transit","out_for_delivery","delivered","cancelled","returned","refunded"];
  const items = o.items.map(i => `<tr><td>${esc(i.name)}</td><td>${esc(i.size||"-")}</td><td>${i.qty}</td><td>${rs(i.price)}</td><td>${esc(i.hsn_code||"-")}</td><td>${rs(i.tax_amount||0)}</td><td>${rs(i.price*i.qty)}</td></tr>`).join("");
  const opts = allStatuses.map(s => `<option ${o.status===s?"selected":""}>${s}</option>`).join("");
  const timeline = (o.status_history||[]).map(h => `<div class="chip">${statusPill(h.status)} ${new Date(h.created_at).toLocaleString("en-IN")} ${h.note?'— '+esc(h.note):''}</div>`).join("");
  const m = modal("Order " + o.id, `
    <div class="grid2">
      <div><h3>Customer</h3>
        <p>${esc(o.customer_name)}<br>${esc(o.phone)}<br>${esc(o.email||"")}</p>
        <p class="muted">${esc(o.address)}, ${esc(o.city)}, ${esc(o.state)} - ${esc(o.pincode)}<br>${esc(o.landmark||"")}</p>
        ${o.gst_number?`<p>GSTIN: ${esc(o.gst_number)}</p>`:''}
      </div>
      <div><h3>Payment</h3>
        <p>Method: <b>${esc(o.payment_method)}</b><br>Status: ${esc(o.payment_status)}<br>Invoice: ${esc(o.invoice_number||'-')}<br>${o.coupon_code?("Coupon: "+esc(o.coupon_code)):""}</p>
        ${o.partial_paid?`<p>Partial: ₹${o.partial_paid} paid, ₹${o.partial_remaining} remaining</p>`:''}
        <p class="muted">${o.razorpay_order_id?("RZP: "+esc(o.razorpay_order_id)):""}</p>
      </div>
    </div>
    <h3>Items</h3>
    <table><thead><tr><th>Product</th><th>Size</th><th>Qty</th><th>Price</th><th>HSN</th><th>Tax</th><th>Total</th></tr></thead><tbody>${items}</tbody></table>
    <p style="text-align:right;margin-top:12px">Subtotal: ${rs(o.subtotal)} &nbsp; Discount: -${rs(o.discount)} &nbsp; Shipping: ${rs(o.shipping)}<br>
    ${o.cgst?`CGST: ${rs(o.cgst)} SGST: ${rs(o.sgst)}`:`IGST: ${rs(o.igst)}`} &nbsp; Tax: ${rs(o.tax_amount)}<br>
    <b style="font-size:18px">Total: ${rs(o.total)}</b></p>
    ${timeline?`<h3>Status History</h3><div class="chips">${timeline}</div>`:''}
    <h3 style="margin-top:14px">Shipping</h3>
    <div class="grid3">
      <div class="field"><label>Courier</label><input id="o_courier" value="${esc(o.courier||"")}"></div>
      <div class="field"><label>Tracking Number</label><input id="o_tracking" value="${esc(o.tracking_number||"")}"></div>
      <div class="field"><label>Tracking URL</label><input id="o_track_url" value="${esc(o.tracking_url||"")}"></div>
    </div>
    <div class="grid2">
      <div class="field"><label>Update status</label><select id="o_status">${opts}</select></div>
      <div class="field"><label>Status note</label><input id="o_note" placeholder="Optional note"></div>
    </div>
  `, `<button class="btn gray" id="mCancel">Close</button><button class="btn ghost" id="mShip">Save Shipping</button><button class="btn" id="mSave">Save Status</button>`);
  $("#mCancel", m).onclick = closeModal;
  $("#mShip", m).onclick = async () => {
    try {
      await api(`/api/admin/orders/${o.id}/shipping`, { method: "PUT", json: {
        courier: $("#o_courier", m).value, tracking_number: $("#o_tracking", m).value, tracking_url: $("#o_track_url", m).value
      }});
      toast("Shipping updated"); closeModal(); VIEWS.orders();
    } catch (e) { toast(e.message, true); }
  };
  $("#mSave", m).onclick = async () => {
    try { await api(`/api/admin/orders/${o.id}/status`, { method: "PUT", json: { status: $("#o_status", m).value, note: $("#o_note", m).value } }); toast("Status updated"); closeModal(); VIEWS.orders(); }
    catch (e) { toast(e.message, true); }
  };
}

/* ---- Customers ---- */
VIEWS.customers = async () => {
  const v = $("#view");
  const list = await api("/api/admin/customers");
  v.innerHTML = `<div class="panel">
    <table><thead><tr><th>ID</th><th>Phone</th><th>Name</th><th>Email</th><th>GST</th><th>Joined</th></tr></thead>
    <tbody>${list.map(c => `<tr>
      <td>${c.id}</td><td>${esc(c.phone)}</td><td>${esc(c.name||'-')}</td><td>${esc(c.email||'-')}</td><td>${esc(c.gst_number||'-')}</td>
      <td class="muted">${c.created_at?new Date(c.created_at).toLocaleDateString("en-IN"):'-'}</td>
    </tr>`).join("")}</tbody></table>
    <p class="muted" style="margin-top:10px">${list.length} customer(s)</p>
  </div>`;
};

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

/* ---- Combos ---- */
VIEWS.combos = async () => {
  const v = $("#view");
  const list = await api("/api/admin/combos");
  v.innerHTML = `<div class="panel"><div class="toolbar"><button class="btn" id="cbAdd">+ Create Combo</button></div>
    <table><thead><tr><th>Name</th><th>Discount</th><th>Products</th><th>Active</th><th></th></tr></thead>
    <tbody>${list.map(c => `<tr>
      <td><b>${esc(c.name)}</b><br><span class="muted">${esc(c.description||'')}</span></td>
      <td>${c.discount_type==='percent'?c.discount_value+'%':c.bundle_price?rs(c.bundle_price):rs(c.discount_value)+' off'}</td>
      <td>${c.items.map(i=>`<span class="chip">${esc(i.product_name||i.product_id)}${i.is_trigger?' (trigger)':''}</span>`).join('')}</td>
      <td>${c.active?'<span class="pill green">Yes</span>':'<span class="pill gray">No</span>'}</td>
      <td><div class="row-actions"><button class="btn sm ghost" data-e="${c.id}">Edit</button><button class="btn sm red" data-d="${c.id}">Del</button></div></td>
    </tr>`).join("")}</tbody></table></div>`;
  const openCombo = async (combo) => {
    combo = combo || { items: [], discount_type: 'percent', active: true };
    if (!CACHE.products.length) CACHE.products = await api("/api/products?include_inactive=true");
    const prodOpts = CACHE.products.map(p => `<option value="${p.id}">${esc(p.name)} (${rs(p.price)})</option>`).join("");
    const m = modal(combo.id ? "Edit Combo" : "Create Combo", `
      <div class="field"><label>Name *</label><input id="cb_name" value="${esc(combo.name||'')}"></div>
      <div class="field"><label>Description</label><input id="cb_desc" value="${esc(combo.description||'')}"></div>
      <div class="grid3">
        <div class="field"><label>Discount Type</label><select id="cb_dtype">
          <option value="percent" ${combo.discount_type==='percent'?'selected':''}>Percent</option>
          <option value="flat" ${combo.discount_type==='flat'?'selected':''}>Flat</option>
          <option value="bundle" ${combo.discount_type==='bundle'?'selected':''}>Bundle Price</option>
        </select></div>
        <div class="field"><label>Discount Value</label><input id="cb_dval" type="number" value="${combo.discount_value||0}"></div>
        <div class="field"><label>Bundle Price (if type=bundle)</label><input id="cb_bprice" type="number" value="${combo.bundle_price||0}"></div>
      </div>
      <h3>Products in combo</h3>
      <div id="cb_items">${(combo.items||[]).map((it,i) => `<div class="toolbar" style="margin-bottom:8px">
        <select class="cb_pid grow"><option value="">Select…</option>${CACHE.products.map(p=>`<option value="${p.id}" ${p.id===it.product_id?'selected':''}>${esc(p.name)}</option>`).join("")}</select>
        <label class="chip"><input type="checkbox" class="cb_trigger" ${it.is_trigger?'checked':''}> Trigger</label>
        <button class="btn sm red cb_rem">X</button>
      </div>`).join("")}</div>
      <button class="btn ghost sm" id="cb_add_item">+ Add product</button>
      <br><label class="chip" style="margin-top:12px"><input type="checkbox" id="cb_active" ${combo.active!==false?'checked':''}> Active</label>
    `, `<button class="btn gray" id="mCancel">Cancel</button><button class="btn" id="mSave">Save</button>`);
    $("#mCancel", m).onclick = closeModal;
    const addItemRow = () => {
      const d = el(`<div class="toolbar" style="margin-bottom:8px">
        <select class="cb_pid grow"><option value="">Select…</option>${prodOpts}</select>
        <label class="chip"><input type="checkbox" class="cb_trigger"> Trigger</label>
        <button class="btn sm red cb_rem">X</button>
      </div>`);
      $(".cb_rem", d).onclick = () => d.remove();
      $("#cb_items", m).appendChild(d);
    };
    m.querySelectorAll(".cb_rem").forEach(b => b.onclick = () => b.closest(".toolbar").remove());
    $("#cb_add_item", m).onclick = addItemRow;
    $("#mSave", m).onclick = async () => {
      const items = [...m.querySelectorAll("#cb_items .toolbar")].map(row => ({
        product_id: $(".cb_pid", row).value,
        is_trigger: $(".cb_trigger", row).checked,
      })).filter(i => i.product_id);
      const payload = {
        name: $("#cb_name", m).value.trim(),
        description: $("#cb_desc", m).value.trim(),
        discount_type: $("#cb_dtype", m).value,
        discount_value: parseFloat($("#cb_dval", m).value) || 0,
        bundle_price: parseFloat($("#cb_bprice", m).value) || 0,
        active: $("#cb_active", m).checked,
        items: items,
      };
      if (!payload.name) { toast("Name required", true); return; }
      try {
        if (combo.id) await api("/api/admin/combos/" + combo.id, { method: "PUT", json: payload });
        else await api("/api/admin/combos", { method: "POST", json: payload });
        toast("Saved"); closeModal(); VIEWS.combos();
      } catch (e) { toast(e.message, true); }
    };
  };
  $("#cbAdd").onclick = () => openCombo();
  v.querySelectorAll("[data-e]").forEach(b => b.onclick = () => openCombo(list.find(c => c.id === parseInt(b.dataset.e))));
  v.querySelectorAll("[data-d]").forEach(b => b.onclick = async () => { if (!confirm("Delete combo?")) return; await api("/api/admin/combos/" + b.dataset.d, { method: "DELETE" }); toast("Deleted"); VIEWS.combos(); });
};

/* ---- Import / Export ---- */
VIEWS.import = async () => {
  const v = $("#view");
  v.innerHTML = `<div class="panel"><h3>Export</h3>
    <p class="muted">Download all products as Excel.</p>
    <div class="toolbar">
      <button class="btn ghost" id="dlTemplate">Download template</button>
      <button class="btn" id="dlExport">Export all products (.xlsx)</button>
    </div></div>
    <div class="panel"><h3>Import (Excel / CSV)</h3>
    <p class="muted">Columns: id, name, category_id, concerns, price, mrp, rating, reviews_count, emoji, badge, image, description, benefits, sizes, hsn_code, gst_rate, stock, active.</p>
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
      $("#impResult").innerHTML = `<div class="panel" style="margin-top:14px"><b style="color:var(--green-700)">${r.created} created, ${r.updated} updated.</b>
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
    <table><thead><tr><th>Code</th><th>Type</th><th>Value</th><th>Min</th><th>Max Disc</th><th>Used</th><th>Limit</th><th>Active</th><th></th></tr></thead>
    <tbody>${list.map(c => `<tr><td><b>${esc(c.code)}</b></td><td>${esc(c.type)}</td><td>${c.type==="percent"?c.value+"%":rs(c.value)}</td>
      <td>${rs(c.min_order)}</td><td>${c.max_discount?rs(c.max_discount):'-'}</td><td>${c.used_count||0}</td><td>${c.usage_limit||'∞'}</td>
      <td>${c.active?'<span class="pill green">Yes</span>':'<span class="pill gray">No</span>'}</td>
      <td><div class="row-actions"><button class="btn sm ghost" data-e='${esc(JSON.stringify(c))}'>Edit</button><button class="btn sm red" data-d="${esc(c.code)}">Del</button></div></td></tr>`).join("")}</tbody></table></div>`;
  const open = (c) => {
    c = c || { type: "percent", active: true };
    const m = modal((c.code?"Edit ":"Add ")+"coupon", `
      <div class="grid2"><div class="field"><label>Code *</label><input id="c_code" value="${esc(c.code||"")}" ${c.code?"disabled":""}></div>
      <div class="field"><label>Type</label><select id="c_type">
        <option value="percent" ${c.type==="percent"?"selected":""}>Percent (%)</option>
        <option value="flat" ${c.type==="flat"?"selected":""}>Flat (₹)</option>
        <option value="free_shipping" ${c.type==="free_shipping"?"selected":""}>Free Shipping</option>
      </select></div></div>
      <div class="grid3"><div class="field"><label>Value</label><input id="c_value" type="number" value="${c.value??0}"></div>
      <div class="field"><label>Min order (₹)</label><input id="c_min" type="number" value="${c.min_order??0}"></div>
      <div class="field"><label>Max discount (₹)</label><input id="c_maxd" type="number" value="${c.max_discount??0}"></div></div>
      <div class="grid3"><div class="field"><label>Usage limit</label><input id="c_limit" type="number" value="${c.usage_limit??0}" placeholder="0=unlimited"></div>
      <div class="field"><label>Per user limit</label><input id="c_pul" type="number" value="${c.per_user_limit??0}"></div>
      <div class="field"><label>Scope</label><select id="c_scope">
        ${['all','category','product','influencer','referral'].map(s => `<option ${c.coupon_scope===s?'selected':''}>${s}</option>`).join('')}
      </select></div></div>
      <div class="chips">
        <label class="chip"><input type="checkbox" id="c_active" ${c.active!==false?"checked":""}> Active</label>
        <label class="chip"><input type="checkbox" id="c_first" ${c.first_order_only?"checked":""}> First order only</label>
      </div>`,
      `<button class="btn gray" id="mCancel">Cancel</button><button class="btn" id="mSave">Save</button>`);
    $("#mCancel", m).onclick = closeModal;
    $("#mSave", m).onclick = async () => {
      const payload = {
        code: c.code || $("#c_code", m).value,
        type: $("#c_type", m).value,
        value: parseFloat($("#c_value", m).value)||0,
        min_order: parseFloat($("#c_min", m).value)||0,
        max_discount: parseFloat($("#c_maxd", m).value)||0,
        usage_limit: parseInt($("#c_limit", m).value)||0,
        per_user_limit: parseInt($("#c_pul", m).value)||0,
        coupon_scope: $("#c_scope", m).value,
        active: $("#c_active", m).checked,
        first_order_only: $("#c_first", m).checked,
      };
      if (!payload.code) { toast("Code required", true); return; }
      try { await api("/api/admin/coupons", { method: "POST", json: payload }); toast("Saved"); closeModal(); VIEWS.coupons(); }
      catch (e) { toast(e.message, true); }
    };
  };
  $("#cAdd").onclick = () => open();
  v.querySelectorAll("[data-e]").forEach(b => b.onclick = () => open(JSON.parse(b.dataset.e)));
  v.querySelectorAll("[data-d]").forEach(b => b.onclick = async () => { if (!confirm("Delete coupon?")) return; await api("/api/admin/coupons/" + encodeURIComponent(b.dataset.d), { method: "DELETE" }); toast("Deleted"); VIEWS.coupons(); });
};

/* ---- Reviews ---- */
VIEWS.reviews = async () => {
  const v = $("#view");
  const list = await api("/api/admin/reviews");
  v.innerHTML = `<div class="panel">
    <div class="toolbar">
      <button class="btn ghost ${!list.some(r=>!r.approved)?'':'amber'}" id="rvPending">Pending (${list.filter(r=>!r.approved).length})</button>
      <button class="btn ghost" id="rvAll">All (${list.length})</button>
    </div>
    <div id="rvTable"></div></div>`;
  const renderList = (items) => {
    $("#rvTable").innerHTML = `<table><thead><tr><th>Product</th><th>Rating</th><th>Title</th><th>Body</th><th>Verified</th><th>Status</th><th></th></tr></thead>
      <tbody>${items.map(r => `<tr>
        <td>${esc(r.product_id)}</td><td>${'★'.repeat(r.rating)}</td><td>${esc(r.title||'-')}</td><td>${esc((r.body||'').substring(0,60))}</td>
        <td>${r.verified_purchase?'<span class="pill green">Yes</span>':'No'}</td>
        <td>${r.approved?'<span class="pill green">Approved</span>':'<span class="pill amber">Pending</span>'}</td>
        <td><div class="row-actions">
          ${!r.approved?`<button class="btn sm ghost" data-approve="${r.id}">Approve</button>`:''}
          <button class="btn sm red" data-del="${r.id}">Del</button>
        </div></td></tr>`).join("")}</tbody></table>`;
    v.querySelectorAll("[data-approve]").forEach(b => b.onclick = async () => { await api("/api/admin/reviews/"+b.dataset.approve+"/approve", {method:"PUT"}); toast("Approved"); VIEWS.reviews(); });
    v.querySelectorAll("[data-del]").forEach(b => b.onclick = async () => { if (!confirm("Delete?")) return; await api("/api/admin/reviews/"+b.dataset.del, {method:"DELETE"}); toast("Deleted"); VIEWS.reviews(); });
  };
  renderList(list.filter(r => !r.approved));
  $("#rvPending").onclick = () => renderList(list.filter(r => !r.approved));
  $("#rvAll").onclick = () => renderList(list);
};

/* ---- Returns ---- */
VIEWS.returns = async () => {
  const v = $("#view");
  const list = await api("/api/admin/returns");
  v.innerHTML = `<div class="panel">
    <table><thead><tr><th>ID</th><th>Order</th><th>Reason</th><th>Status</th><th>Refund</th><th></th></tr></thead>
    <tbody>${list.map(r => `<tr>
      <td>${r.id}</td><td>${esc(r.order_id)}</td><td>${esc(r.reason||'-')}</td>
      <td><span class="pill ${r.status==='requested'?'amber':r.status==='approved'||r.status==='refunded'?'green':'red'}">${r.status}</span></td>
      <td>${r.refund_amount?rs(r.refund_amount):'-'}</td>
      <td><button class="btn sm ghost" data-e='${esc(JSON.stringify(r))}'>Manage</button></td>
    </tr>`).join("")}</tbody></table></div>`;
  v.querySelectorAll("[data-e]").forEach(b => b.onclick = () => {
    const r = JSON.parse(b.dataset.e);
    const m = modal("Return #" + r.id, `
      <p>Order: <b>${esc(r.order_id)}</b><br>Reason: ${esc(r.reason||'Not specified')}</p>
      ${(r.images||[]).length?`<div class="toolbar">${r.images.map(i=>`<img src="${esc(i)}" style="height:60px">`).join('')}</div>`:''}
      <div class="grid2">
        <div class="field"><label>Status</label><select id="rt_status">
          ${['requested','approved','rejected','refunded','partial_refunded'].map(s=>`<option ${r.status===s?'selected':''}>${s}</option>`).join('')}
        </select></div>
        <div class="field"><label>Refund Amount</label><input id="rt_amount" type="number" value="${r.refund_amount||0}"></div>
      </div>
      <div class="field"><label>Refund Method</label><select id="rt_method">
        ${['','original','bank','wallet'].map(s=>`<option ${r.refund_method===s?'selected':''}>${s||'Select…'}</option>`).join('')}
      </select></div>
      <div class="field"><label>Admin Notes</label><textarea id="rt_notes" rows="2">${esc(r.admin_notes||'')}</textarea></div>
    `, `<button class="btn gray" id="mCancel">Cancel</button><button class="btn" id="mSave">Update</button>`);
    $("#mCancel", m).onclick = closeModal;
    $("#mSave", m).onclick = async () => {
      try {
        await api("/api/admin/returns/" + r.id, { method: "PUT", json: {
          status: $("#rt_status", m).value,
          refund_amount: parseFloat($("#rt_amount", m).value)||0,
          refund_method: $("#rt_method", m).value,
          admin_notes: $("#rt_notes", m).value,
        }});
        toast("Updated"); closeModal(); VIEWS.returns();
      } catch (e) { toast(e.message, true); }
    };
  });
};

/* ---- Inventory ---- */
VIEWS.inventory = async () => {
  const v = $("#view");
  const [products, logs] = await Promise.all([api("/api/admin/reports/inventory"), api("/api/admin/inventory-logs")]);
  const low = products.filter(p => p.is_low);
  const out = products.filter(p => p.is_out);
  v.innerHTML = `<div class="cards">
    <div class="card"><div class="k">Total Products</div><div class="v">${products.length}</div></div>
    <div class="card" style="${out.length?'background:#fef2f2':''}"><div class="k">Out of Stock</div><div class="v">${out.length}</div></div>
    <div class="card" style="${low.length?'background:#fefce8':''}"><div class="k">Low Stock</div><div class="v">${low.length}</div></div>
  </div>
  ${low.length?`<div class="panel"><h3>Low Stock Products</h3><table><thead><tr><th>Product</th><th>Stock</th><th>Threshold</th></tr></thead>
    <tbody>${low.map(p=>`<tr><td>${esc(p.name)}</td><td><b style="color:${p.is_out?'var(--red)':'#ca8a04'}">${p.stock}</b></td><td>${p.low_stock_threshold}</td></tr>`).join('')}</tbody></table></div>`:''}
  <div class="panel"><h3>Recent Inventory Changes</h3>
    <table><thead><tr><th>Product</th><th>Change</th><th>Reason</th><th>Note</th><th>Date</th></tr></thead>
    <tbody>${logs.slice(0,50).map(l=>`<tr>
      <td>${esc(l.product_id)}</td><td><b style="color:${l.change>0?'var(--green-700)':'var(--red)'}">${l.change>0?'+':''}${l.change}</b></td>
      <td>${esc(l.reason)}</td><td class="muted">${esc(l.note)}</td>
      <td class="muted">${new Date(l.created_at).toLocaleString("en-IN")}</td>
    </tr>`).join('')}</tbody></table></div>`;
};

/* ---- Influencers ---- */
VIEWS.influencers = async () => {
  const v = $("#view");
  const list = await api("/api/admin/influencers");
  v.innerHTML = `<div class="panel"><div class="toolbar"><button class="btn" id="infAdd">+ Add Influencer</button></div>
    <table><thead><tr><th>Name</th><th>Code</th><th>Coupon</th><th>Commission</th><th>Orders</th><th>Revenue</th><th>Status</th><th></th></tr></thead>
    <tbody>${list.map(i => `<tr>
      <td><b>${esc(i.name)}</b><br><span class="muted">${esc(i.email||i.phone||'')}</span></td>
      <td>${esc(i.referral_code)}</td><td>${esc(i.coupon_code||'-')}</td><td>${i.commission_percent}%</td>
      <td>${i.total_orders||0}</td><td>${rs(i.total_revenue||0)}</td>
      <td><span class="pill ${i.status==='approved'?'green':i.status==='pending'?'amber':'red'}">${i.status}</span></td>
      <td><div class="row-actions"><button class="btn sm ghost" data-e='${esc(JSON.stringify(i))}'>Edit</button><button class="btn sm red" data-d="${i.id}">Del</button></div></td>
    </tr>`).join("")}</tbody></table></div>`;
  const openInf = (inf) => {
    inf = inf || { commission_percent: 5, status: 'pending' };
    const m = modal(inf.id ? "Edit Influencer" : "Add Influencer", `
      <div class="grid2">
        <div class="field"><label>Name *</label><input id="inf_name" value="${esc(inf.name||'')}"></div>
        <div class="field"><label>Email</label><input id="inf_email" value="${esc(inf.email||'')}"></div>
      </div>
      <div class="grid2">
        <div class="field"><label>Phone</label><input id="inf_phone" value="${esc(inf.phone||'')}"></div>
        <div class="field"><label>Referral Code</label><input id="inf_code" value="${esc(inf.referral_code||'')}"></div>
      </div>
      <div class="grid2">
        <div class="field"><label>Coupon Code</label><input id="inf_coupon" value="${esc(inf.coupon_code||'')}"></div>
        <div class="field"><label>Commission %</label><input id="inf_comm" type="number" value="${inf.commission_percent||5}"></div>
      </div>
      <div class="field"><label>Status</label><select id="inf_status">
        ${['pending','approved','rejected','suspended'].map(s=>`<option ${inf.status===s?'selected':''}>${s}</option>`).join('')}
      </select></div>
    `, `<button class="btn gray" id="mCancel">Cancel</button><button class="btn" id="mSave">Save</button>`);
    $("#mCancel", m).onclick = closeModal;
    $("#mSave", m).onclick = async () => {
      const payload = {
        name: $("#inf_name", m).value.trim(),
        email: $("#inf_email", m).value.trim(),
        phone: $("#inf_phone", m).value.trim(),
        referral_code: $("#inf_code", m).value.trim(),
        coupon_code: $("#inf_coupon", m).value.trim(),
        commission_percent: parseFloat($("#inf_comm", m).value)||5,
        status: $("#inf_status", m).value,
      };
      if (!payload.name) { toast("Name required", true); return; }
      try {
        if (inf.id) await api("/api/admin/influencers/" + inf.id, { method: "PUT", json: payload });
        else await api("/api/admin/influencers", { method: "POST", json: payload });
        toast("Saved"); closeModal(); VIEWS.influencers();
      } catch (e) { toast(e.message, true); }
    };
  };
  $("#infAdd").onclick = () => openInf();
  v.querySelectorAll("[data-e]").forEach(b => b.onclick = () => openInf(JSON.parse(b.dataset.e)));
  v.querySelectorAll("[data-d]").forEach(b => b.onclick = async () => { if (!confirm("Delete?")) return; await api("/api/admin/influencers/"+b.dataset.d, {method:"DELETE"}); toast("Deleted"); VIEWS.influencers(); });
};

/* ---- Blog ---- */
VIEWS.blog = async () => {
  const v = $("#view");
  const list = await api("/api/admin/blog/posts");
  v.innerHTML = `<div class="panel"><div class="toolbar"><button class="btn" id="blogAdd">+ New Post</button></div>
    <table><thead><tr><th>Title</th><th>Author</th><th>Status</th><th>Views</th><th>Date</th><th></th></tr></thead>
    <tbody>${list.map(p => `<tr>
      <td><b>${esc(p.title)}</b><br><span class="muted">${esc(p.slug)}</span></td>
      <td>${esc(p.author)}</td>
      <td>${p.published?'<span class="pill green">Published</span>':'<span class="pill gray">Draft</span>'}</td>
      <td>${p.views||0}</td>
      <td class="muted">${new Date(p.created_at).toLocaleDateString("en-IN")}</td>
      <td><div class="row-actions"><button class="btn sm ghost" data-e="${p.id}">Edit</button><button class="btn sm red" data-d="${p.id}">Del</button></div></td>
    </tr>`).join("")}</tbody></table></div>`;
  const openPost = async (post) => {
    post = post || {};
    if (post.id) {
      try { post = await api("/api/blog/posts/" + (post.slug || post.id)); } catch(e) {}
    }
    const m = modal(post.id ? "Edit Post" : "New Blog Post", `
      <div class="field"><label>Title *</label><input id="bp_title" value="${esc(post.title||'')}"></div>
      <div class="grid2">
        <div class="field"><label>Slug</label><input id="bp_slug" value="${esc(post.slug||'')}"></div>
        <div class="field"><label>Author</label><input id="bp_author" value="${esc(post.author||'PrimeNutra Wellness')}"></div>
      </div>
      <div class="field"><label>Excerpt</label><textarea id="bp_excerpt" rows="2">${esc(post.excerpt||'')}</textarea></div>
      <div class="field"><label>Body (HTML)</label><textarea id="bp_body" rows="8">${esc(post.body||'')}</textarea></div>
      <div class="field"><label>Cover Image URL</label><input id="bp_cover" value="${esc(post.cover_image||'')}"></div>
      <div class="field"><label>Tags (comma separated)</label><input id="bp_tags" value="${esc((post.tags||[]).join(', '))}"></div>
      <div class="grid2">
        <div class="field"><label>SEO Title</label><input id="bp_seo_t" value="${esc(post.seo_title||'')}"></div>
        <div class="field"><label>SEO Description</label><input id="bp_seo_d" value="${esc(post.seo_description||'')}"></div>
      </div>
      <label class="chip"><input type="checkbox" id="bp_pub" ${post.published?'checked':''}> Published</label>
    `, `<button class="btn gray" id="mCancel">Cancel</button><button class="btn" id="mSave">Save</button>`);
    $("#mCancel", m).onclick = closeModal;
    $("#mSave", m).onclick = async () => {
      const payload = {
        title: $("#bp_title", m).value.trim(),
        slug: $("#bp_slug", m).value.trim(),
        author: $("#bp_author", m).value.trim(),
        excerpt: $("#bp_excerpt", m).value.trim(),
        body: $("#bp_body", m).value,
        cover_image: $("#bp_cover", m).value.trim(),
        tags: $("#bp_tags", m).value.split(',').map(s=>s.trim()).filter(Boolean),
        seo_title: $("#bp_seo_t", m).value.trim(),
        seo_description: $("#bp_seo_d", m).value.trim(),
        published: $("#bp_pub", m).checked,
      };
      if (!payload.title) { toast("Title required", true); return; }
      try {
        if (post.id) await api("/api/admin/blog/posts/" + post.id, { method: "PUT", json: payload });
        else await api("/api/admin/blog/posts", { method: "POST", json: payload });
        toast("Saved"); closeModal(); VIEWS.blog();
      } catch (e) { toast(e.message, true); }
    };
  };
  $("#blogAdd").onclick = () => openPost();
  v.querySelectorAll("[data-e]").forEach(b => b.onclick = () => openPost(list.find(p => p.id === parseInt(b.dataset.e))));
  v.querySelectorAll("[data-d]").forEach(b => b.onclick = async () => { if (!confirm("Delete post?")) return; await api("/api/admin/blog/posts/"+b.dataset.d, {method:"DELETE"}); toast("Deleted"); VIEWS.blog(); });
};

/* ---- Reports ---- */
VIEWS.reports = async () => {
  const v = $("#view");
  v.innerHTML = `<div class="panel"><h3>Revenue Report</h3>
    <div class="toolbar">
      <select id="rp_days"><option value="7">7 days</option><option value="30" selected>30 days</option><option value="90">90 days</option><option value="365">1 year</option></select>
      <button class="btn" id="rp_load">Load</button>
    </div>
    <div id="rp_rev"></div></div>
  <div class="panel"><h3>Top Products</h3><div id="rp_prod"></div></div>
  <div class="panel"><h3>GST Summary</h3><div id="rp_gst"></div></div>
  <div class="panel"><h3>Export Reports</h3>
    <div class="toolbar">
      <a class="btn ghost" href="/api/admin/reports/export/orders?days=30" target="_blank">Orders CSV</a>
      <a class="btn ghost" href="/api/admin/reports/export/products" target="_blank">Products CSV</a>
      <a class="btn ghost" href="/api/admin/reports/export/customers" target="_blank">Customers CSV</a>
      <a class="btn ghost" href="/api/admin/reports/export/gst?days=30" target="_blank">GST CSV</a>
    </div></div>`;
  const load = async () => {
    const days = $("#rp_days").value;
    const [rev, prod, gst] = await Promise.all([
      api("/api/admin/reports/revenue?days=" + days),
      api("/api/admin/reports/products?days=" + days),
      api("/api/admin/reports/gst?days=" + days),
    ]);
    $("#rp_rev").innerHTML = `<div class="cards">
      <div class="card"><div class="k">Revenue</div><div class="v">${rs(rev.total_revenue)}</div></div>
      <div class="card"><div class="k">Orders</div><div class="v">${rev.total_orders}</div></div>
      <div class="card"><div class="k">Avg Order</div><div class="v">${rs(rev.avg_order_value)}</div></div>
      <div class="card"><div class="k">Tax Collected</div><div class="v">${rs(rev.total_tax)}</div></div>
      <div class="card"><div class="k">Discounts</div><div class="v">${rs(rev.total_discount)}</div></div>
    </div>`;
    $("#rp_prod").innerHTML = `<table><thead><tr><th>Product</th><th>Qty Sold</th><th>Revenue</th></tr></thead>
      <tbody>${prod.slice(0,20).map(p=>`<tr><td>${esc(p.name)}</td><td>${p.qty_sold}</td><td>${rs(p.revenue)}</td></tr>`).join('')}</tbody></table>`;
    $("#rp_gst").innerHTML = `<div class="cards">
      <div class="card"><div class="k">Total Tax</div><div class="v">${rs(gst.total_tax)}</div></div>
      <div class="card"><div class="k">CGST</div><div class="v">${rs(gst.cgst)}</div></div>
      <div class="card"><div class="k">SGST</div><div class="v">${rs(gst.sgst)}</div></div>
      <div class="card"><div class="k">IGST</div><div class="v">${rs(gst.igst)}</div></div>
    </div>`;
  };
  $("#rp_load").onclick = load;
  load();
};

/* ---- Notifications ---- */
VIEWS.notifications = async () => {
  const v = $("#view");
  const list = await api("/api/admin/notifications");
  v.innerHTML = `<div class="panel">
    <table><thead><tr><th>Channel</th><th>To</th><th>Event</th><th>Subject</th><th>Status</th><th>Date</th></tr></thead>
    <tbody>${list.map(n => `<tr>
      <td><span class="pill ${n.channel==='email'?'green':'amber'}">${n.channel}</span></td>
      <td>${esc(n.recipient)}</td><td>${esc(n.event_type)}</td><td>${esc(n.subject)}</td>
      <td><span class="pill ${n.status==='sent'?'green':n.status==='failed'?'red':'gray'}">${n.status}</span></td>
      <td class="muted">${n.created_at?new Date(n.created_at).toLocaleString("en-IN"):''}</td>
    </tr>`).join("")}</tbody></table>
    <p class="muted" style="margin-top:10px">${list.length} notification(s)</p></div>`;
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
      <div class="field"><label>WhatsApp number</label><input id="s_whatsapp_number" value="${esc(s.whatsapp_number||"")}"></div>
    </div>
    <div class="grid2">
      <div class="field"><label>Support email</label><input id="s_support_email" value="${esc(s.support_email||"")}"></div>
      <div class="field"><label>Support phone</label><input id="s_support_phone" value="${esc(s.support_phone||"")}"></div>
    </div>
  </div>
  <div class="panel"><h3>Shipping</h3>
    <div class="grid2">
      <div class="field"><label>Shipping fee (₹)</label><input id="s_shipping_fee" type="number" value="${esc(s.shipping_fee||"0")}"></div>
      <div class="field"><label>Free ship threshold (₹)</label><input id="s_free_ship_threshold" type="number" value="${esc(s.free_ship_threshold||"0")}"></div>
    </div>
  </div>
  <div class="panel"><h3>Payments</h3>
    <div class="chips" style="margin-bottom:12px">
      <label class="chip"><input type="checkbox" id="s_cod_enabled" ${chk("cod_enabled")}> COD enabled</label>
      <label class="chip"><input type="checkbox" id="s_razorpay_enabled" ${chk("razorpay_enabled")}> Razorpay enabled</label>
      <label class="chip"><input type="checkbox" id="s_partial_payment_enabled" ${chk("partial_payment_enabled")}> Partial payment</label>
    </div>
    <div class="grid3">
      <div class="field"><label>COD charge (₹)</label><input id="s_cod_charge" type="number" value="${esc(s.cod_charge||"0")}"></div>
      <div class="field"><label>COD min order (₹)</label><input id="s_cod_min_order" type="number" value="${esc(s.cod_min_order||"0")}"></div>
      <div class="field"><label>Partial min advance (₹)</label><input id="s_partial_min_advance" type="number" value="${esc(s.partial_min_advance||"500")}"></div>
    </div>
    <div class="grid2">
      <div class="field"><label>Razorpay Key ID</label><input id="s_razorpay_key_id" value="${esc(s.razorpay_key_id||"")}" placeholder="rzp_live_…"></div>
      <div class="field"><label>Razorpay Key Secret</label><input id="s_razorpay_key_secret" type="password" placeholder="Leave blank to keep current"></div>
    </div>
  </div>
  <div class="panel"><h3>GST & Invoice</h3>
    <div class="grid2">
      <div class="field"><label>Company name</label><input id="s_company_name" value="${esc(s.company_name||"")}"></div>
      <div class="field"><label>GST Number</label><input id="s_gst_number" value="${esc(s.gst_number||"")}"></div>
    </div>
    <div class="grid2">
      <div class="field"><label>Company address</label><input id="s_company_address" value="${esc(s.company_address||"")}"></div>
      <div class="field"><label>Company state</label><input id="s_company_state" value="${esc(s.company_state||"")}"></div>
    </div>
    <div class="field" style="max-width:200px"><label>Invoice prefix</label><input id="s_invoice_prefix" value="${esc(s.invoice_prefix||"INV")}"></div>
  </div>
  <div class="panel"><h3>Email (Brevo)</h3>
    <div class="grid2">
      <div class="field"><label>From name</label><input id="s_brevo_from_name" value="${esc(s.brevo_from_name||"")}"></div>
      <div class="field"><label>From email</label><input id="s_brevo_from_email" value="${esc(s.brevo_from_email||"")}"></div>
    </div>
    <div class="field"><label>Brevo API key</label><input id="s_brevo_api_key" value="${esc(s.brevo_api_key||"")}" placeholder="xkeysib-…"></div>
  </div>
  <div class="panel"><h3>WhatsApp API</h3>
    <div class="grid2">
      <div class="field"><label>API URL</label><input id="s_whatsapp_api_url" value="${esc(s.whatsapp_api_url||"")}"></div>
      <div class="field"><label>API Key</label><input id="s_whatsapp_api_key" value="${esc(s.whatsapp_api_key||"")}" type="password"></div>
    </div>
  </div>
  <div class="panel"><h3>OTP Settings</h3>
    <div class="grid3">
      <div class="field"><label>Provider</label><select id="s_otp_provider">
        <option value="console" ${s.otp_provider==='console'?'selected':''}>Console (dev)</option>
        <option value="msg91" ${s.otp_provider==='msg91'?'selected':''}>MSG91</option>
        <option value="twilio" ${s.otp_provider==='twilio'?'selected':''}>Twilio</option>
      </select></div>
      <div class="field"><label>API Key</label><input id="s_otp_api_key" value="${esc(s.otp_api_key||"")}" type="password"></div>
      <div class="field"><label>Sender ID</label><input id="s_otp_sender_id" value="${esc(s.otp_sender_id||"")}"></div>
    </div>
  </div>
  <div class="panel"><h3>Analytics</h3>
    <div class="grid2">
      <div class="field"><label>GA4 Measurement ID</label><input id="s_ga4_measurement_id" value="${esc(s.ga4_measurement_id||"")}"></div>
      <div class="field"><label>GTM Container ID</label><input id="s_gtm_container_id" value="${esc(s.gtm_container_id||"")}"></div>
    </div>
    <div class="grid2">
      <div class="field"><label>Meta Pixel ID</label><input id="s_meta_pixel_id" value="${esc(s.meta_pixel_id||"")}"></div>
      <div class="field"><label>FB Access Token</label><input id="s_fb_access_token" value="${esc(s.fb_access_token||"")}" type="password"></div>
    </div>
  </div>
  <button class="btn" id="sSave" style="margin-top:8px">Save all settings</button>`;
  $("#sSave").onclick = async () => {
    const keys = ["store_name","whatsapp_number","support_email","support_phone","shipping_fee","free_ship_threshold",
      "cod_charge","cod_min_order","partial_min_advance",
      "razorpay_key_id","razorpay_key_secret","brevo_from_name","brevo_from_email","brevo_api_key",
      "whatsapp_api_url","whatsapp_api_key","otp_api_key","otp_sender_id",
      "company_name","gst_number","company_address","company_state","invoice_prefix",
      "ga4_measurement_id","gtm_container_id","meta_pixel_id","fb_access_token"];
    const values = {};
    keys.forEach(k => { const el = $("#s_" + k); if (el) values[k] = el.value; });
    values.cod_enabled = $("#s_cod_enabled").checked ? "true" : "false";
    values.razorpay_enabled = $("#s_razorpay_enabled").checked ? "true" : "false";
    values.partial_payment_enabled = $("#s_partial_payment_enabled").checked ? "true" : "false";
    const provEl = $("#s_otp_provider"); if (provEl) values.otp_provider = provEl.value;
    // Don't send empty secret to avoid clearing
    if (!values.razorpay_key_secret) delete values.razorpay_key_secret;
    if (!values.whatsapp_api_key) delete values.whatsapp_api_key;
    if (!values.otp_api_key) delete values.otp_api_key;
    if (!values.fb_access_token) delete values.fb_access_token;
    try { await api("/api/admin/settings", { method: "PUT", json: { values } }); toast("Settings saved"); }
    catch (e) { toast(e.message, true); }
  };
};

/* ---- SEO & Redirects ---- */
VIEWS.seo = async () => {
  const v = $("#view");
  const list = await api("/api/admin/redirects");
  v.innerHTML = `<div class="panel"><h3>301 Redirects</h3>
    <p class="muted">Manage URL redirects for SEO. Old URLs will redirect to new URLs.</p>
    <div class="toolbar">
      <input id="rd_from" placeholder="/old-path" class="grow">
      <input id="rd_to" placeholder="/new-path" class="grow">
      <button class="btn" id="rdAdd">Add redirect</button>
    </div>
    <table><thead><tr><th>From</th><th>To</th><th>Type</th><th></th></tr></thead>
    <tbody>${list.map(r => `<tr><td>${esc(r.from_path)}</td><td>${esc(r.to_path)}</td><td>${r.type}</td>
      <td><button class="btn sm red" data-d="${r.id}">Del</button></td></tr>`).join("")}</tbody></table></div>
  <div class="panel"><h3>SEO Endpoints</h3>
    <p class="muted">These are auto-generated:</p>
    <ul><li><a href="/sitemap.xml" target="_blank">/sitemap.xml</a></li>
    <li><a href="/robots.txt" target="_blank">/robots.txt</a></li></ul>
  </div>`;
  $("#rdAdd").onclick = async () => {
    const from = $("#rd_from").value.trim(), to = $("#rd_to").value.trim();
    if (!from || !to) { toast("Both paths required", true); return; }
    try { await api("/api/admin/redirects?from_path="+encodeURIComponent(from)+"&to_path="+encodeURIComponent(to), { method: "POST" }); toast("Added"); VIEWS.seo(); }
    catch (e) { toast(e.message, true); }
  };
  v.querySelectorAll("[data-d]").forEach(b => b.onclick = async () => { await api("/api/admin/redirects/"+b.dataset.d, {method:"DELETE"}); toast("Deleted"); VIEWS.seo(); });
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
