import os
from celery import Celery

# Configure Celery to use Redis as broker and backend
# Make sure redis-server is running on localhost:6379, or fallback to sqlite for local dev if needed.
# We will use Redis as requested.
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "cadastre_worker",
    broker=redis_url,
    backend=redis_url,
    include=["backend.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_pool="solo"  # Required for Windows compatibility
)
