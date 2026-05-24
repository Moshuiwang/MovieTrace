#!/usr/bin/env bash
# P1.57l: End-to-end upgrade + rebuild verification
# Usage: ./scripts/verify_p1_57_upgrade_rebuild.sh [DB_PATH]
# Runs against a COPY of the database (original never modified)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

DB_PATH="${1:-data/movietrace.db}"
if [ ! -f "$DB_PATH" ]; then
  echo "ERROR: DB not found: $DB_PATH" >&2
  exit 1
fi

# 1. Create a temp copy (never modify original)
TS=$(date +%Y%m%d_%H%M%S)
TMP_DB=$(mktemp /tmp/movietrace_upgrade_verify_${TS}_XXXXXX.db)
cp "$DB_PATH" "$TMP_DB"
echo "[1/6] DB copy: $TMP_DB"

# 2. Record baseline content_updates count
BEFORE_CU=$(PYTHONPATH=src .venv/bin/python -c "
import sqlite3; c=sqlite3.connect('$TMP_DB')
print(c.execute('select count(*) from content_updates').fetchone()[0])
")
echo "[2/6] content_updates before: $BEFORE_CU"

# 3. Apply migrations
echo "[3/6] Running migrate..."
PYTHONPATH=src .venv/bin/python -m movietrace.cli migrate --db "$TMP_DB"

# 4. Verify schema version = 19
V=$(PYTHONPATH=src .venv/bin/python -c "
import sqlite3; c=sqlite3.connect('$TMP_DB')
print(c.execute('select max(version) from schema_migrations').fetchone()[0])
")
echo "[4/6] schema_version after migrate: $V"
if [ "$V" != "19" ]; then echo "ERROR: expected version 19, got $V"; rm -f "$TMP_DB"; exit 1; fi

# 5. Run backfill
echo "[5/6] Running backfill --commit..."
PYTHONPATH=src .venv/bin/python scripts/p1_57_backfill_current_discovery.py --db "$TMP_DB" --commit

# 6. Verify content_updates unchanged
AFTER_CU=$(PYTHONPATH=src .venv/bin/python -c "
import sqlite3; c=sqlite3.connect('$TMP_DB')
print(c.execute('select count(*) from content_updates').fetchone()[0])
")
echo "[6/6] content_updates after: $AFTER_CU"
if [ "$BEFORE_CU" != "$AFTER_CU" ]; then
  echo "ERROR: content_updates count changed: $BEFORE_CU -> $AFTER_CU"; rm -f "$TMP_DB"; exit 1
fi

# Check current_discovery_items created (A1: assert count >= expected)
CDI=$(PYTHONPATH=src .venv/bin/python -c "
import sqlite3; c=sqlite3.connect('$TMP_DB')
print(c.execute('select count(*) from current_discovery_items').fetchone()[0])
")
echo "current_discovery_items: $CDI"
OBS=$(PYTHONPATH=src .venv/bin/python -c "
import sqlite3; c=sqlite3.connect('$TMP_DB')
print(c.execute('select count(*) from discovery_observations').fetchone()[0])
")
echo "discovery_observations: $OBS"

# A1: Compute expected minimum counts from new_discovery rows that have a parseable
# discovery key (format: discovery:{movie|tv}:{tmdb_id}:{date}).
# The number of distinct (content_type, tmdb_id) pairs is the minimum expected CDI count.
EXPECTED_CDI=$(PYTHONPATH=src .venv/bin/python -c "
import sqlite3, re
c = sqlite3.connect('$TMP_DB')
rows = c.execute(\"SELECT content_update_id FROM content_updates WHERE update_type='new_discovery'\").fetchall()
keys = set()
for (cid,) in rows:
    if not cid:
        continue
    parts = cid.split(':')
    if len(parts) >= 4 and parts[0] == 'discovery' and parts[1] in ('movie', 'tv') and parts[2].isdigit() and re.match(r'^\d{4}-\d{2}-\d{2}$', parts[3]):
        keys.add((parts[1], parts[2]))
print(len(keys))
")
echo "expected_min_current_discovery_items (distinct discovery keys): $EXPECTED_CDI"

# Assert CDI >= expected minimum
if [ -n "$EXPECTED_CDI" ] && [ "$EXPECTED_CDI" -gt 0 ]; then
  if [ "$CDI" -lt "$EXPECTED_CDI" ]; then
    echo "ERROR: current_discovery_items count $CDI < expected minimum $EXPECTED_CDI"; rm -f "$TMP_DB"; exit 1
  fi
  echo "ASSERT OK: current_discovery_items $CDI >= $EXPECTED_CDI"
fi

# Assert OBS >= CDI (at least one observation per item)
if [ "$OBS" -lt "$CDI" ]; then
  echo "ERROR: discovery_observations count $OBS < current_discovery_items count $CDI"; rm -f "$TMP_DB"; exit 1
fi
echo "ASSERT OK: discovery_observations $OBS >= current_discovery_items $CDI"

# 7. Export recommendations (uses temp DB)
echo "[7/7] Running export-recommendations (dry-run check)..."
PYTHONPATH=src .venv/bin/python -m movietrace.cli export-recommendations --db "$TMP_DB" --days 30 --dry-run

rm -f "$TMP_DB"
echo ""
echo "P1.57l upgrade/rebuild verification PASSED"
echo "   Upgrade steps for production:"
echo "   1. Backup DB"
echo "   2. PYTHONPATH=src python -m movietrace.cli migrate"
echo "   3. PYTHONPATH=src python scripts/p1_57_backfill_current_discovery.py --commit"
echo "   4. PYTHONPATH=src python -m movietrace.cli export-recommendations"
echo "   5. PYTHONPATH=src python -m movietrace.cli sync-feishu-table (uses stable keys)"
