
#!/bin/bash

VARIANTS_DIR=~/gnss/captures/conj_variants

CONFIG=~/gnss/configs/conj_test.conf

RESULTS=~/gnss/runs/conj_results.txt

echo "variant,IF,tracking_starts,losses,bit_sync,nav_messages,carrier_lock_min" > $RESULTS



for variant in orig conj swapIQ swapIQ_conj; do

    for IF in 500000 -500000; do

        echo "=== Testing $variant IF=$IF ==="

        

        sed -i "s|SignalSource.filename=.*|SignalSource.filename=$VARIANTS_DIR/lime_${variant}.dat|" $CONFIG

        sed -i "s|InputFilter.IF=.*|InputFilter.IF=$IF|" $CONFIG

        

        RUN_ID=$(date -u +%Y%m%d_%H%M%S)

        RUN_DIR=~/gnss/runs/conj_${variant}_IF${IF}_${RUN_ID}

        mkdir -p "$RUN_DIR"

        

        cd "$RUN_DIR"

        timeout 90s gnss-sdr --config_file=$CONFIG > run.log 2>&1

        

        LOG_INT=$(ls -t /tmp/gnss-sdr.hft02.rrama28.log.INFO.* | head -1)

        

        STARTS=$(grep -c "Tracking of GPS" run.log 2>/dev/null || echo 0)

        LOSSES=$(grep -c "Loss of lock" run.log 2>/dev/null || echo 0)

        BITSYNC=$(grep -c "tracking bit synchronization" run.log 2>/dev/null || echo 0)

        NAV=$(grep -c "NAV message" run.log 2>/dev/null || echo 0)

        MIN_CARRIER=$(grep "carrier_lock_fail_counter" $LOG_INT | grep -oP 'carrier_lock_fail_counter:\K[0-9]+' | sort -n | head -1)

        

        echo "$variant,$IF,$STARTS,$LOSSES,$BITSYNC,$NAV,${MIN_CARRIER:-NA}" | tee -a $RESULTS

        echo "--- bit_sync=$BITSYNC nav=$NAV min_carrier=${MIN_CARRIER:-NA} ---"

    done

done



echo "=== DONE ==="

cat $RESULTS

