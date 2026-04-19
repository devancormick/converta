.PHONY: dev test lint migrate train rollback build

dev:
	docker compose -f infra/docker/docker-compose.yml up

build:
	docker compose -f infra/docker/docker-compose.yml build

test:
	pytest tests/ -v --cov=. --cov-report=term-missing

lint:
	ruff check . && mypy .

migrate:
	alembic upgrade head

train:
	python training/train_classifier.py

rollback:
	@test -n "$(MODEL)" || (echo "Usage: make rollback MODEL=<version>" && exit 1)
	python -c "import mlflow; client = mlflow.tracking.MlflowClient(); client.set_registered_model_alias('quality-classifier', 'champion', '$(MODEL)'); print('Rolled back champion to version $(MODEL)')"

retrain-ci:
	python training/train_classifier.py --compare-champion --promote-if-better

golden-eval:
	pytest tests/regression/ -v
