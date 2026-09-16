.PHONY: install widget run docker test smoke ingest

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	cd widget && npm install && npm run build

widget:
	cd widget && npm install && npm run build

run:
	PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --reload --port 8000

ingest:
	PYTHONPATH=. .venv/bin/python -m backend.app.rag.ingest

docker:
	docker compose up --build

test:
	PYTHONPATH=. .venv/bin/pytest -q

smoke:
	@curl -sf http://localhost:8000/health >/dev/null && echo "health ok"
	@curl -sf http://localhost:8000/api/v1/public-config >/dev/null && echo "public-config ok"
	@curl -sf -o /dev/null -w "standalone %{http_code}\n" http://localhost:8000/
	@curl -sf -o /dev/null -w "widget %{http_code}\n" http://localhost:8000/widget/consultant.js
