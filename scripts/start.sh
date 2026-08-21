#!/usr/bin/env sh
set -eu

docker compose -f infra/compose.yaml up --build
