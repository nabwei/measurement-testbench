#!/usr/bin/env bash
# Real software-timestamp PTP packets on an isolated veth pair; never adjusts clocks.
set -euo pipefail
if [[ $(id -u) != 0 ]]; then
  echo 'BLOCKED: root/CAP_NET_ADMIN required for task-owned network namespaces.' >&2
  exit 2
fi
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
output=${1:?Supply a fresh output directory}
mkdir -- "$output"
output=$(cd -- "$output" && pwd)
left="portfolio-ptp-a-$$"
right="portfolio-ptp-b-$$"
left_created=0
right_created=0
pids=()
socket_dir=''
cleanup() {
  local original_status=$?
  local cleanup_failed=0
  trap - EXIT INT TERM
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || true; done
  if (( left_created )); then ip netns delete "$left" || cleanup_failed=1; fi
  if (( right_created )); then ip netns delete "$right" || cleanup_failed=1; fi
  if [[ -n "$socket_dir" ]]; then
    rm -f -- "$socket_dir/a" "$socket_dir/a-ro" "$socket_dir/b" "$socket_dir/b-ro" || cleanup_failed=1
    rmdir -- "$socket_dir" || cleanup_failed=1
  fi
  if (( cleanup_failed )); then echo 'FAIL: one or more task-owned cleanup operations failed' >&2; fi
  if (( original_status )); then exit "$original_status"; fi
  exit "$cleanup_failed"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
socket_dir=$(mktemp -d /tmp/portfolio-ptp.XXXXXX)
ip netns add "$left"
left_created=1
ip netns add "$right"
right_created=1
ip -n "$left" link add ptpa type veth peer name ptpb netns "$right"
ip -n "$left" address add 192.0.2.1/30 dev ptpa
ip -n "$right" address add 192.0.2.2/30 dev ptpb
ip -n "$left" link set ptpa up
ip -n "$right" link set ptpb up
ip -n "$left" link set lo up
ip -n "$right" link set lo up
for side in a b; do
  cat > "$output/$side.cfg" <<EOF
[global]
time_stamping software
free_running 1
domainNumber 93
logSyncInterval -3
logAnnounceInterval -1
logging_level 6
use_syslog 0
verbose 1
uds_address $socket_dir/$side
uds_ro_address $socket_dir/$side-ro
EOF
done
ptp4l -v > "$output/version.txt"
ip netns exec "$left" timeout --signal=TERM --kill-after=5s 30s ptp4l -S -i ptpa -f "$output/a.cfg" --priority1 100 > "$output/server.log" 2>&1 &
pids+=("$!")
ip netns exec "$right" timeout --signal=TERM --kill-after=5s 30s ptp4l -S -s -i ptpb -f "$output/b.cfg" > "$output/client.log" 2>&1 &
pids+=("$!")
for pid in "${pids[@]}"; do
  code=0
  wait "$pid" || code=$?
  if [[ $code != 124 ]]; then
    echo "FAIL: expected bounded capture timeout, got $code; inspect daemon logs" >&2
    exit 1
  fi
done
pids=()
"$script_dir/../.venv/bin/python" "$script_dir/analyze_ptp_log.py" "$output/client.log" --provenance SOFTWARE_ONLY --output "$output/report.json"
echo 'PASS: software PTP packet exchange; both endpoints share host CLOCK_REALTIME, free_running=1, no independent clock synchronization claim.'
