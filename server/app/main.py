"""PrimeNutra Wellness — FastAPI entry point."""
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import DATA_DIR, UPLOAD_DIR
from .database import Base, engine, SessionLocal
from .models import Redirect

# ─── Create tables ───
Base.metadata.create_all(bind=engine)

# ─── Seed data ───
from .seed import run_seed
run_seed()

# ─── App ───
app = FastAPI(title="PrimeNutra Wellness API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static / uploads ───
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

ADMIN_DIR = os.path.join(STATIC_DIR, "admin")

# ─── Routers ───
from .routers.admin import router as admin_router
from .routers.products import router as products_router
from .routers.categories import router as categories_router
from .routers.orders import router as orders_router
from .routers.payments import router as payments_router
from .routers.auth import router as auth_router
from .routers.customer_auth import router as customer_auth_router
from .routers.customer import router as customer_router
from .routers.combos import router as combos_router
from .routers.blog import router as blog_router
from .routers.influencer import router as influencer_router
from .routers.reports import router as reports_router

for r in [
    admin_router, products_router, categories_router, orders_router,
    payments_router, auth_router, customer_auth_router, customer_router,
    combos_router, blog_router, influencer_router, reports_router,
]:
    app.include_router(r)


# ─── SEO routes ───

@app.get("/api/public/settings")
def public_settings():
    from .utils import get_public_settings
    db = SessionLocal()
    try:
        return get_public_settings(db)
    finally:
        db.close()


@app.get("/sitemap.xml")
def sitemap_xml():
    from fastapi.responses import Response
    from .models import Product, BlogPost, Category
    db = SessionLocal()
    try:
        base = "https://primenutrawellness.in"
        urls = [
            f"<url><loc>{base}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>",
            f"<url><loc>{base}/about.html</loc><changefreq>monthly</changefreq></url>",
            f"<url><loc>{base}/contact.html</loc><changefreq>monthly</changefreq></url>",
            f"<url><loc>{base}/blog.html</loc><changefreq>weekly</changefreq></url>",
        ]
        for p in db.query(Product).filter(Product.active == True).all():
            urls.append(f"<url><loc>{base}/product.html?id={p.id}</loc><changefreq>weekly</changefreq></url>")
        for c in db.query(Category).all():
            urls.append(f"<url><loc>{base}/index.html?category={c.id}</loc><changefreq>weekly</changefreq></url>")
        for b in db.query(BlogPost).filter(BlogPost.published == True).all():
            urls.append(f"<url><loc>{base}/blog.html?slug={b.slug}</loc><changefreq>weekly</changefreq></url>")
        xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>"
        return Response(content=xml, media_type="application/xml")
    finally:
        db.close()


@app.get("/robots.txt")
def robots_txt():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        "User-agent: *\nAllow: /\nSitemap: https://primenutrawellness.in/sitemap.xml\n"
    )


# ─── 301 Redirect middleware ───
@app.middleware("http")
async def redirect_middleware(request: Request, call_next):
    path = request.url.path
    db = SessionLocal()
    try:
        redir = db.query(Redirect).filter(Redirect.from_path == path).first()
        if redir:
            return RedirectResponse(url=redir.to_path, status_code=redir.type)
    finally:
        db.close()
    return await call_next(request)


# ─── Admin HTML ───
@app.get("/admin")
@app.get("/admin/")
@app.get("/admin/{path:path}")
def admin_page(path: str = ""):
    from fastapi.responses import FileResponse
    index = os.path.join(ADMIN_DIR, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return JSONResponse({"error": "Admin panel not found"}, status_code=404)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


# ─── Serve storefront (HTML/CSS/JS) ───
# The storefront files sit one level above `server/`
STOREFRONT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_STOREFRONT_FILES = [
    "index.html", "shop.html", "product.html", "checkout.html",
    "about.html", "blog.html", "contact.html", "account.html",
    "track.html", "wishlist.html",
]

for _page in _STOREFRONT_FILES:
    _filepath = os.path.join(STOREFRONT_DIR, _page)
    if os.path.isfile(_filepath):
        _route = "/" + _page
        # Use default param to capture the value at definition time
        def _make_handler(fp):
            def _handler():
                from fastapi.responses import FileResponse
                return FileResponse(fp)
            return _handler
        app.get(_route, include_in_schema=False)(_make_handler(_filepath))

# Mount CSS/JS directories
for _subdir in ["css", "js", "images"]:
    _dirpath = os.path.join(STOREFRONT_DIR, _subdir)
    if os.path.isdir(_dirpath):
        app.mount("/" + _subdir, StaticFiles(directory=_dirpath), name="storefront_" + _subdir)

# Serve index.html at root
@app.get("/", include_in_schema=False)
def root_page():
    from fastapi.responses import FileResponse
    index = os.path.join(STOREFRONT_DIR, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return JSONResponse({"message": "PrimeNutra Wellness API", "docs": "/docs"})
