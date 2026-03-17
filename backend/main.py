from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import FastAPI

from backend.routes.analyze import router as analyze_router
from backend.utils.logging_utils import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Market Analyst", version="0.1.0")
app.include_router(analyze_router)


@app.get("/health")
def health() -> Dict[str, Any]:
    request_id = str(uuid.uuid4())
    logger.info("health request_id=%s", request_id)
    return {"request_id": request_id, "status": "ok"}

