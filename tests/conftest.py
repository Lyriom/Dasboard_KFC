from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_kfc_app_installs.db")
os.environ.setdefault("AUTH_DISABLED", "true")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

