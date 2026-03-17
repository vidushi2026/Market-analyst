from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter

from backend.agents.fundamental import FundamentalAgent
from backend.agents.sentiment import SentimentAgent
from backend.agents.technical import TechnicalAgent
from backend.orchestrator.orchestrator import Orchestrator
from backend.services.search_service import SearchService
from backend.services.yahoo_service import YahooService
from backend.utils.cache import TTLCache
from backend.utils.logging_utils import get_logger
from backend.utils.metrics import metrics
from models.schemas import (
    AnalyzePortfolioRequest,
    AnalyzeStockRequest,
    ApiError,
    ApiResponse,
    CompareRequest,
)

logger = get_logger(__name__)
router = APIRouter()

_cache = TTLCache()
_yahoo = YahooService(cache=_cache)
_search = SearchService(cache=_cache)
_orchestrator = Orchestrator(
    fundamental=FundamentalAgent(_yahoo),
    technical=TechnicalAgent(_yahoo),
    sentiment=SentimentAgent(_search),
)


def _ok(data: Dict[str, Any], request_id: str) -> ApiResponse:
    return ApiResponse(request_id=request_id, status="ok", data=data)


def _err(code: str, message: str, request_id: str, details: Dict[str, Any] | None = None) -> ApiResponse:
    return ApiResponse(
        request_id=request_id,
        status="error",
        error=ApiError(code=code, message=message, details=details or {}),
    )


@router.post("/analyze/stock", response_model=ApiResponse, response_model_exclude_none=True)
def analyze_stock(req: AnalyzeStockRequest) -> ApiResponse:
    request_id = str(uuid.uuid4())
    logger.info("api.analyze_stock.start request_id=%s ticker=%s", request_id, req.ticker)
    metrics.inc("api_analyze_stock_requests")
    try:
        data = _orchestrator.analyze_stock(req.ticker, period=req.options.period or "6mo", interval=req.options.interval or "1d")
        metrics.inc("api_analyze_stock_ok")
        return _ok(data=data, request_id=request_id)
    except Exception as e:  # noqa: BLE001
        logger.info("api.analyze_stock.error request_id=%s err=%s", request_id, str(e))
        metrics.inc("api_analyze_stock_error")
        return _err("INTERNAL_ERROR", "Failed to analyze stock.", request_id, {"exception": str(e)})


@router.post("/compare", response_model=ApiResponse, response_model_exclude_none=True)
def compare(req: CompareRequest) -> ApiResponse:
    request_id = str(uuid.uuid4())
    left, right = req.stocks[0], req.stocks[1]
    logger.info("api.compare.start request_id=%s left=%s right=%s", request_id, left, right)
    metrics.inc("api_compare_requests")
    try:
        data = _orchestrator.compare(left, right, period=req.options.period or "6mo", interval=req.options.interval or "1d")
        metrics.inc("api_compare_ok")
        return _ok(data=data, request_id=request_id)
    except Exception as e:  # noqa: BLE001
        logger.info("api.compare.error request_id=%s err=%s", request_id, str(e))
        metrics.inc("api_compare_error")
        return _err("INTERNAL_ERROR", "Failed to compare stocks.", request_id, {"exception": str(e)})


@router.post("/analyze/portfolio", response_model=ApiResponse, response_model_exclude_none=True)
def analyze_portfolio(req: AnalyzePortfolioRequest) -> ApiResponse:
    request_id = str(uuid.uuid4())
    logger.info("api.analyze_portfolio.start request_id=%s n=%s", request_id, len(req.portfolio))
    metrics.inc("api_analyze_portfolio_requests")
    try:
        items = [{"ticker": p.ticker, "weight": p.weight} for p in req.portfolio]
        data = _orchestrator.analyze_portfolio(items, period=req.options.period or "6mo", interval=req.options.interval or "1d")
        metrics.inc("api_analyze_portfolio_ok")
        return _ok(data=data, request_id=request_id)
    except Exception as e:  # noqa: BLE001
        logger.info("api.analyze_portfolio.error request_id=%s err=%s", request_id, str(e))
        metrics.inc("api_analyze_portfolio_error")
        return _err("INTERNAL_ERROR", "Failed to analyze portfolio.", request_id, {"exception": str(e)})

