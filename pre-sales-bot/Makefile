.PHONY: install run test ingest finetune docker smoke

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

run:
	PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --reload --port 8010

test:
	PYTHONPATH=. .venv/bin/pytest -q

ingest:
	PYTHONPATH=. .venv/bin/python -m backend.app.rag.ingest

finetune:
	PYTHONPATH=. .venv/bin/python -m backend.app.learning.finetune --tenant $(TENANT)

docker:
	docker compose up --build

smoke:
	@curl -sf http://localhost:8010/health >/dev/null && echo "health ok"
	@curl -sf "http://localhost:8010/api/v1/public-config?tenant=demo" >/dev/null && echo "public-config ok"
	@curl -sf -o /dev/null -w "standalone %{http_code}\n" http://localhost:8010/
	@curl -sf -o /dev/null -w "widget %{http_code}\n" http://localhost:8010/widget/consultant.js
