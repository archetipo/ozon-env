#!/bin/bash
echo "update system"
poetry update
echo "make compose"
docker-compose up -d
echo "check code"
poetry run black ozonenv/**/*.py
poetry run flake8 ozonenv/**/*.py
pip install --upgrade -e .
echo "run test"
poetry run pytest --cov --cov-report=html -vv
docker-compose down
rm -rf tests/models
echo "make project: Done."
