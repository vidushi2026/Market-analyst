from backend.agents.sentiment import SentimentAgent


class FakeSearch:
    def get_news(self, query: str, max_results: int = 8, window: str = "7d"):
        return {
            "query": query,
            "as_of": "2026-01-01T00:00:00Z",
            "items": [
                {"title": "Company beats earnings estimates", "url": "x"},
                {"title": "Shares surge after record profit", "url": "y"},
            ],
        }


def test_sentiment_agent_positive_with_positive_headlines():
    agent = SentimentAgent(search=FakeSearch())
    out = agent.run("TEST")
    assert out["status"] == "ok"
    assert out["sentiment"] == "positive"
    assert out["score"] >= 7

