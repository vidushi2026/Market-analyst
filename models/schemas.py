from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ApiResponse(BaseModel):
    request_id: str
    status: Literal["ok", "error"]
    data: Optional[Dict[str, Any]] = None
    error: Optional[ApiError] = None


class AnalyzeStockOptions(BaseModel):
    period: Optional[str] = "6mo"
    interval: Optional[str] = "1d"
    include_portfolio_engine: bool = False


class AnalyzeStockRequest(BaseModel):
    ticker: str
    options: AnalyzeStockOptions = Field(default_factory=AnalyzeStockOptions)


class CompareRequest(BaseModel):
    stocks: List[str] = Field(min_length=2, max_length=2)
    options: AnalyzeStockOptions = Field(default_factory=AnalyzeStockOptions)


class PortfolioItem(BaseModel):
    ticker: str
    weight: float = Field(ge=0, le=1)


class AnalyzePortfolioRequest(BaseModel):
    portfolio: List[PortfolioItem] = Field(min_length=1)
    options: AnalyzeStockOptions = Field(default_factory=AnalyzeStockOptions)

