.PHONY: demo seed build dbt test eval lint clean

PY ?= python
export PYTHONPATH := src

demo: seed build dbt test eval ## pipeline completo

seed: ## dataset determinístico (semente 3)
	@echo "==> gerando dados"
	@$(PY) data/generate.py

build: ## contrato -> schema.yml + testes singulares + docs
	@echo "==> compilando contratos"
	@$(PY) -m contract_agent.cli

dbt: ## materializa e roda os testes gerados
	@echo "==> dbt build"
	@cd dbt && DBT_PROFILES_DIR=. $(PY) -m dbt.cli.main deps --project-dir .
	@cd dbt && DBT_PROFILES_DIR=. $(PY) -m dbt.cli.main build --project-dir .

test: ## testes do gerador
	@echo "==> pytest"
	@$(PY) -m pytest tests -q --cov=contract_agent --cov-report=term-missing

eval: ## avaliação por mutação
	@$(PY) evals/runner.py

lint:
	@$(PY) -m ruff check src tests evals data

clean:
	@rm -rf data/raw warehouse.duckdb dbt/target dbt/logs dbt/dbt_packages .pytest_cache .coverage .ruff_cache
