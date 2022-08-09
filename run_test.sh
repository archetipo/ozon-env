#!/bin/bash
echo "update system"
poetry update
echo "init service"
. env/bin/activate
docker-compose up -d
echo "check code"
poetry run black ozonenv/**/*.py
poetry run flake8 ozonenv/**/*.py
poetry run bandit ozonenv/**/*.py
echo "run test"
poetry run pytest --cov
docker-compose down
echo "make project: Done."
