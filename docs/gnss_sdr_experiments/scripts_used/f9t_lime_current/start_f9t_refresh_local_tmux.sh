#!/usr/bin/env bash
set -euo pipefail

DURATION="${1:-600}"
SESSION="f9t_local_refresh_$(date -u +%Y%m%d_%H%M%S)"

tmux new -d -s "$SESSION" "$HOME/gnss/scripts/refresh_f9t_xml_local.sh $DURATION"

echo "Started tmux session: $SESSION"
echo "Duration: ${DURATION}s"
echo ""
echo "Attach with:"
echo "tmux attach -t $SESSION"
echo ""
echo "Watch latest local log with:"
echo "tail -f \$(ls -t ~/gnss/f9t/logs/refresh_local_*.log | head -1)"
