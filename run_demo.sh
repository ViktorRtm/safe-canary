#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pytest -q tests
python3 scripts/generate_fixture.py
python3 scripts/evaluate.py
python3 scripts/route.py 0 --no-reload
docker compose build stable
docker compose up -d --no-build
python3 scripts/smoke.py
python3 scripts/route.py 5
python3 scripts/probe_traffic.py --requests 500 --workers 12
python3 scripts/assess_canary.py --expect-rejection
python3 scripts/rollback_check.py
printf '\nREPORTS: reports/quality.json reports/canary_traffic.json reports/canary_assessment.json reports/rollback_proof.json\n'
docker compose down
