#!/bin/sh
PRESSED="10"
RELEASED="0"
TIMEOUT_MS=10000   # 10 秒超時

# Try to find odin_evtest from available USB drives
findEvtestPath() {
    for path in /run/media/sda1 /run/media/sdb1 /run/media/sdb2; do
        if [ -x "$path/dqa_package/odin_evtest" ]; then
            echo "$path/dqa_package/odin_evtest"
            return
        fi
    done
    echo ""
}

# Find odin_evtest path before doing anything
EVTEST_PATH=$(findEvtestPath)

if [ -z "$EVTEST_PATH" ]; then
    echo "Error: odin_evtest not found in any USB device!"
    exit 1
else
    echo "odin_evtest found at: $EVTEST_PATH"
fi

# Get current time in milliseconds
getCurrentMillisecond() {
    echo $(($(date +%s%N)/1000000))
}

# Check power key state
isPowerKeyPressed() {
    "$EVTEST_PATH" --query /dev/input/event1 EV_KEY 116
    echo "$?"
}

start_time=$(getCurrentMillisecond)

while true; do
    key_state=$(isPowerKeyPressed)
    now_ms=$(getCurrentMillisecond)
    elapsed=$((now_ms - start_time))

    if [ "$key_state" = "$PRESSED" ]; then
        echo "Key pressed!"
        echo "PASS"
        exit 0
    fi

    # timeout check
    if [ $elapsed -ge $TIMEOUT_MS ]; then
        echo "Timeout: no key press detected within 10 seconds"
        echo "FAIL"
        exit 1
    fi

    sleep 0.1  # avoid busy loop
done

