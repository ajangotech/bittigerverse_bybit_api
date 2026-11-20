#!/usr/bin/env bash
set -euo pipefail

docker compose build --no-cache
docker compose up -d

echo
echo "BitTiger services deployed."
docker compose ps
