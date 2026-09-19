#!/usr/bin/env bash
# Threshold Phase-1 smoke test: bring the stack up and drive ONE engagement
# against the bundled Juice Shop, auto-approving each stage, until a report
# exists. Requires Docker + a GOOGLE_API_KEY (or ANTHROPIC_API_KEY) in .env.
#
# This is the SINGLE-run Phase-1 milestone check only. The full 10x READY gate
# is Phase 4 and is not implemented yet. Best-effort: the state/approval polling
# assumes the current /api shape and may need adjustment once run live.
set -euo pipefail

API="${THRESHOLD_API:-http://localhost:8000}"
TARGET="${THRESHOLD_TARGET:-http://juice-shop:3000/}"

echo "[smoke] bringing the stack up (first build can take a long time)..."
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d --build

echo "[smoke] waiting for the orchestrator to answer at $API ..."
for _ in $(seq 1 60); do
  if curl -fsS "$API/api/state" >/dev/null 2>&1; then break; fi
  sleep 5
done

echo "[smoke] starting an engagement against $TARGET"
curl -fsS -X POST "$API/api/engagement" -H 'Content-Type: application/json' \
  -d "{\"message\": \"assess $TARGET\"}"
echo

echo "[smoke] auto-approving stages until the run finishes..."
for stage in recon exploit post_exploit analysis report; do
  for _ in $(seq 1 120); do
    pending="$(curl -fsS "$API/api/state" \
      | python -c "import sys,json;d=json.load(sys.stdin);pa=d.get('pending_action') or {};print(pa.get('stage',''))" 2>/dev/null || true)"
    if [ "$pending" = "$stage" ]; then
      echo "[smoke] approving $stage"
      curl -fsS -X POST "$API/api/approvals" -H 'Content-Type: application/json' \
        -d "{\"stage\": \"$stage\", \"decision\": \"approved\"}" >/dev/null || true
      break
    fi
    sleep 5
  done
done

echo "[smoke] checking for a generated report in the data volume..."
if docker compose exec -T orchestrator sh -c "ls -1 /data/reports 2>/dev/null | head" | grep -q .; then
  echo "[smoke] PASS: a report was produced."
else
  echo "[smoke] FAIL: no report found. Inspect: docker compose logs orchestrator"
  exit 1
fi
