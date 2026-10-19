IMAGE_NAME ?= hostboard
PORT ?= 8000
export IMAGE_NAME PORT

.PHONY: up down logs test-e2e test-e2e-ui

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

test-e2e:
	npm run test:e2e

test-e2e-ui:
	npm run test:e2e:ui
