import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("CACHE_DIR", "/tmp/elexon_cache")
from main import app  # noqa: E402,F401
