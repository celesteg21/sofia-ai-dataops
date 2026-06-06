#!/usr/bin/env sh
# Chequeo local de calidad para desarrollo.
# Objetivo: correr lint, type-checking y tests con un solo comando antes de commitear.

set -eu

ruff check .
mypy src
pytest
