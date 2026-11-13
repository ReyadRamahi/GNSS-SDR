
#!/bin/bash

set -e



echo "=== Locking ADF4002 to external 10 MHz reference ==="

LimeUtil --refclk="serial=0009061C01502715" --fref=10000000

echo ""



LOCK=$(LimeUtil --refclk="serial=0009061C01502715" --fref=10000000 2>&1 | grep "Lock State")

echo "$LOCK"

if echo "$LOCK" | grep -q "Lock State: 0"; then

    echo "ERROR: ADF4002 failed to lock. Check SiLabs board connection."

    exit 1

fi



echo "=== Starting gnss-sdr ==="

exec gnss-sdr "$@"

