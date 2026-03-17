.PHONY: install dev-backend dev-frontend test lint format docker-build docker-run

install:
	python3 -m pip install -r requirements.txt

dev-backend:
	python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	streamlit run frontend/streamlit_app.py --server.port 8501

test:
	pytest -q

lint:
	ruff check .

format:
	ruff format .

docker-build:
	docker build -t market-analyst:latest .

docker-run:
	docker run --rm -p 8000:8000 market-analyst:latest
