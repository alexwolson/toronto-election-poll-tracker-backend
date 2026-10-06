#!/usr/bin/env bash
# Held-out election sweep for the compact model. Run from the backend root:
#   bash docs/research/compact_mayoral/run_holdouts.sh <runs_dir> "<horizons>" "<variants>" [innovations] [target_accept]
# Each historical campaign's result is nulled in turn and predicted from the polls
# available at the horizon (days before its election). Campaigns with no poll at a
# horizon are skipped (the fit exits nonzero with a clear message).
#
# Pre-registration hygiene (2026-09-22): this script prints sampler diagnostics only.
# Every fit also carries a 2026 forecast; those numbers stay in the run directories
# and are read only after the held-out decision rule has been applied.
set -u
#   4th arg: innovations family (gaussian | student_t); student_t runs get a "-student_t" suffix.
#   5th arg: NUTS target acceptance probability (default 0.9; production uses 0.95).
RUNS="${1:?runs dir}"
HORIZONS="${2:-39 14}"
VARIANTS="${3:-isotropic leaders}"
INNOVATIONS="${4:-gaussian}"
TARGET_ACCEPT="${5:-0.9}"
#   6th arg: corpus (all | from-2010); from-2010 runs get an "_era" suffix and skip 2003/2006.
CORPUS="${6:-all}"
#   7th arg: extra fit arguments passed through verbatim; 8th arg: run-name suffix for them.
EXTRA_ARGS="${7:-}"
EXTRA_SUFFIX="${8:-}"
SUFFIX=""
[ "$INNOVATIONS" = "gaussian" ] || SUFFIX="-${INNOVATIONS}"
[ "$CORPUS" = "all" ] || SUFFIX="${SUFFIX}_era"
SUFFIX="${SUFFIX}${EXTRA_SUFFIX}"
CAMPAIGNS="toronto_2003 toronto_2006 toronto_2010 toronto_2014 toronto_2018 toronto_2022 toronto_2023"
mkdir -p "$RUNS"
for H in $HORIZONS; do
  for C in $CAMPAIGNS; do
    if [ "$CORPUS" != "all" ] && { [ "$C" = "toronto_2003" ] || [ "$C" = "toronto_2006" ]; }; then continue; fi
    for V in $VARIANTS; do
      NAME="holdout${H}-${C}-${V}${SUFFIX}"
      OUT="$RUNS/$NAME"
      if [ -e "$OUT/summary.json" ]; then echo "skip (exists) $OUT"; continue; fi
      # Only ever remove the fully spelled run directory (never a bare parent).
      [ -n "$NAME" ] && [ -d "$OUT" ] && rm -rf "${RUNS:?}/${NAME:?}"
      LOG="$RUNS/$NAME.log"
      if uv run python -m docs.research.compact_mayoral.fit \
          --campaigns all --hyperpriors population --variant "$V" --innovations "$INNOVATIONS" \
          --target-accept "$TARGET_ACCEPT" --corpus "$CORPUS" $EXTRA_ARGS \
          --holdout "$C" --horizon-days "$H" --out "$OUT" > "$LOG" 2>&1; then
        grep -E "^done" "$LOG" | sed "s|^|[$H $C $V $INNOVATIONS] |"
      else
        echo "[$H $C $V $INNOVATIONS] FAILED: $(grep -E 'ValueError|Error' "$LOG" | tail -1)"
        [ -d "$OUT" ] && rm -rf "${RUNS:?}/${NAME:?}"
      fi
    done
  done
done
