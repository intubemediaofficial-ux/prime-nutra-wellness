import os

# Base directory of the server package (……/server)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _writable(path: str) -> bool:
    try:
        os.makedirs(path, exist_ok=True)
        return os.access(path, os.W_OK)
    except OSError:
        return False


# Prefer a mounted volume at /data (Fly.io) so the SQLite DB + uploads persist
# across deploys; otherwise fall back to a local folder for development.
if os.environ.get("PNW_DATA_DIR"):
    _ROOT = os.environ["PNW_DATA_DIR"]
elif _writable("/data"):
    _ROOT = "/data"
else:
    _ROOT = BASE_DIR

DATA_DIR = os.environ.get("PNW_DATA_DIR", os.path.join(_ROOT, "data"))
UPLOAD_DIR = os.environ.get("PNW_UPLOAD_DIR", os.path.join(_ROOT, "uploads"))
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(DATA_DIR, 'pnw.db')}")

# Auth
SECRET_KEY = os.environ.get("PNW_SECRET_KEY", "change-me-in-production-please-set-PNW_SECRET_KEY")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get("PNW_TOKEN_HOURS", "72"))

# Default admin (created on first run if no admin exists)
DEFAULT_ADMIN_USER = os.environ.get("PNW_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("PNW_ADMIN_PASSWORD", "admin12345")

# Optional Brevo (Sendinblue) key for transactional emails; can also be set in admin settings
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")

# CORS: comma separated list of allowed origins ("*" allows all)
CORS_ORIGINS = os.environ.get("PNW_CORS_ORIGINS", "*")
