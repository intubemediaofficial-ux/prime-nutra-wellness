import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import CORS_ORIGINS, UPLOAD_DIR
from .database import Base, SessionLocal, engine
from .routers import admin, auth, categories, orders, payments, products
from .seed import run_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables + seed (admin, settings, catalog) at runtime startup.
    # Kept out of import scope so merely importing `app` has no side effects.
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        run_seed(db)
    yield


app = FastAPI(title="PrimeNutra Wellness API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if CORS_ORIGINS == "*" else [o.strip() for o in CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "primenutra-backend"}


# Uploaded product images
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Admin panel (static SPA)
ADMIN_DIR = os.path.join(os.path.dirname(__file__), "static", "admin")


@app.get("/admin")
def admin_root():
    return RedirectResponse(url="/admin/")


@app.get("/admin/")
def admin_index():
    return FileResponse(os.path.join(ADMIN_DIR, "index.html"))


app.mount("/admin", StaticFiles(directory=ADMIN_DIR, html=True), name="admin")


@app.get("/")
def root():
    return RedirectResponse(url="/admin/")
