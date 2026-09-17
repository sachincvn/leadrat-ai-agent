import os

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
BASE = f"{API_URL}{API_PREFIX}"
REQUEST_TIMEOUT = 180
