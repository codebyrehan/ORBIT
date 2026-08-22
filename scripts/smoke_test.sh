#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

curl --fail --silent --show-error "$BASE_URL/" | grep -q '"status":"ok"'
curl --fail --silent --show-error "$BASE_URL/health" | grep -q '"status":"ok"'
curl --fail --silent --show-error "$BASE_URL/ready" | grep -q '"status":"ready"'
curl --fail --silent --show-error "$BASE_URL/docs" | grep -q 'ORBIT'
curl --fail --silent --show-error "$BASE_URL/v1/metrics" | grep -q 'orbit_requests_total'

export BASE_URL
seq 1 40 | xargs -n1 -P10 -I{} curl --fail --silent --show-error "$BASE_URL/health" >/dev/null

printf 'smoke tests passed for %s\n' "$BASE_URL"
