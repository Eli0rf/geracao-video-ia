.PHONY: install dev test lint typecheck ci clean run help

PYTHON := python3.13
VENV := .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
UVICORN := $(VENV)/bin/uvicorn

## help: Mostra esta ajuda
help:
	@grep -E '^## ' Makefile | sed 's/## //'

## install: Cria venv e instala dependências de produção + dev
install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "✅ Ambiente instalado. Ative com: source .venv/bin/activate"

## install-ai: Instala dependências de IA (torch, diffusers, etc) — pesado!
install-ai:
	$(PIP) install -e ".[ai]"
	@echo "✅ Dependências de IA instaladas."

## run: Roda a API em modo desenvolvimento com hot-reload
run:
	$(UVICORN) src.api.main:app --reload --host 0.0.0.0 --port 8000

## test: Roda todos os testes com cobertura
test:
	$(PYTEST) tests/ --cov=src --cov-report=term-missing --cov-fail-under=80

## test-unit: Roda apenas testes unitários
test-unit:
	$(PYTEST) tests/unit/ -v

## test-integration: Roda apenas testes de integração
test-integration:
	$(PYTEST) tests/integration/ -v

## lint: Verifica estilo e qualidade com ruff
lint:
	$(RUFF) check src/ tests/

## lint-fix: Corrige automaticamente problemas de lint
lint-fix:
	$(RUFF) check --fix src/ tests/

## typecheck: Verifica tipos com mypy
typecheck:
	$(MYPY) src/

## ci: Roda todos os checks do CI localmente (lint + typecheck + tests)
ci: lint typecheck test

## clean: Remove arquivos temporários e cache
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	@echo "✅ Limpeza concluída."

## db-upgrade: Aplica migrations pendentes
db-upgrade:
	$(VENV)/bin/alembic upgrade head

## db-revision: Cria nova migration (uso: make db-revision MSG="descrição")
db-revision:
	$(VENV)/bin/alembic revision --autogenerate -m "$(MSG)"



## ─── Docker / Container ───────────────────────────────────────────────────────

## docker-build: Builda a imagem Docker da API
docker-build:
	@echo "🔨 Buildando imagem: geracao-video-ia:0.1.0"
	docker build --pull -t geracao-video-ia:0.1.0 .
	@echo "✅ Build concluído."

## docker-run: Roda o container API (porta 8000, volume outputs/)
docker-run:
	@echo "🚀 Iniciando container geracao-video-ia-api..."
	docker run --rm -p 8000:8000 		-v $(CURDIR)/outputs:/app/outputs 		-e APP_ENV=production 		geracao-video-ia:0.1.0

## docker-up: Suba a stack via docker compose (build + volumes)
docker-up:
	@echo "🚀 Subindo stack com docker compose..."
	docker compose up -d --build

## docker-down: Pare a stack e remova containers
docker-down:
	@echo "🛑 Parando stack..."
	docker compose down

## docker-logs: Acompanhe os logs do container API
docker-logs:
	@echo "📋 Logs do container API (Ctrl+C para parar)"
	docker compose logs -f api

## docker-clean: Remove container, imagem e volumes (cuidado!)
docker-clean:
	@echo "🗑️  Removendo container, imagem e volumes..."
	docker compose down -v
	docker rmi geracao-video-ia:0.1.0 || true
	@echo "✅ Limpeza concluída."

## docker-shell: Abra um shell no container em execução
docker-shell:
	@echo "🐚 Shell no container..."
	docker compose exec api sh

## docker-test: Roda a suíte de testes DROSA dentro do container
docker-test:
	@echo "🧪 Rodando testes dentro do container..."
	docker compose run --rm api pytest tests/ -v --tb=short
