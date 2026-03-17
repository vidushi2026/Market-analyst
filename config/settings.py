from pydantic import BaseModel


class Settings(BaseModel):
    # Scoring weights (Phase 6)
    weight_fundamental: float = 0.40
    weight_technical: float = 0.35
    weight_sentiment: float = 0.25

    # Cache TTLs (seconds) (Phase 5)
    ttl_prices_intraday: int = 60 * 10
    ttl_prices_daily: int = 60 * 45
    ttl_fundamentals: int = 60 * 60 * 12
    ttl_news: int = 60 * 45

    # Timeouts (seconds) (Phase 4)
    upstream_timeout_seconds: int = 12


settings = Settings()

