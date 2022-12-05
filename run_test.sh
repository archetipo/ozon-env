#!/bin/bash
echo "update system"
poetry update
docker-compose up -d
echo "check code"
poetry run black ozonenv/**/*.py
poetry run flake8 ozonenv/**/*.py
pip install -e .
echo "run test"
poetry run pytest --cov --cov-report=html
docker-compose down
rm -rf tests/models
echo "make project: Done."
