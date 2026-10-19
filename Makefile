# The few commands a reviewer needs. Everything runs in Docker; nothing is installed on the host.
.PHONY: up down logs test eval decide post-sample shell

up:          ## Build and start; migrates and imports the sample on first run
	docker compose up --build -d && echo "http://localhost:8000/review  ·  http://localhost:8000/docs"

down:        ## Stop and remove the containers (the database volume stays)
	docker compose down

logs:        ## Follow the web log
	docker compose logs -f web

test:        ## Run the test suite against Postgres, in the image
	docker compose run --rm web pytest

eval:        ## Score the categoriser against the gold set (see docs/evaluation.md)
	docker compose run --rm web python manage.py evaluate

decide:      ## Try one description: make decide TEXT="Fietsenmaker Van Dam"
	docker compose run --rm web python manage.py decide "$(TEXT)"

post-sample: ## Feed the sample CSV through POST /transactions, one request per row (decision 0006)
	python3 scripts/post_transactions.py --base-url http://localhost:8000 data/transaction_history.csv --quiet

shell:       ## A shell in the web container
	docker compose run --rm web sh
