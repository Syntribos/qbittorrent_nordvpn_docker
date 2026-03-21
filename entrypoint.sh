#!/bin/bash
set -e

#groupadd nordvpn
usermod -aG nordvpn root

if [[ -z "$NORD_TOKEN" ]]; then
    echo ".env must contain a NORD_TOKEN for authentication"
    return 1
fi

if [[ -z "$CONNECT_RETRIES" ]]; then
    CONNECT_RETRIES=10
fi

echo "Starting Nord"
python3 start_nord.py -t "$NORD_TOKEN" -r "$CONNECT_RETRIES"
echo "All done, starting heartbeat..."
exec python3 heartbeat.py
