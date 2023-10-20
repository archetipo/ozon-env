#!/bin/bash
echo "update system"
poetry update
echo "make compose"
docker compose  up -d --force-recreate
echo "check code"
poetry run black ozonenv/**/*.py
#poetry run flake8 ozonenv/**/*.py
pip install --upgrade -e .
pip install aiopath --upgrade
echo "run test"
poetry run pytest --cov --cov-report=html -vv
docker compose down
rm -rf tests/models
echo "make project: Done."
