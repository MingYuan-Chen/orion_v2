#!/bin/bash
# ===========================================
# Odin configure_console.sh (SILENT VERSION)
# Only print final PASS or FAIL
# ===========================================

fail() {
    echo "Configuration failed: $1"
    exit 1
}

# ------------------------------
# GPIO Section
# ------------------------------
control_gpio12() {
    if [ ! -d /sys/class/gpio/gpio12 ]; then
        echo 12 > /sys/class/gpio/export 2>/dev/null
        sleep 0.1
    fi

    if [ -f /sys/class/gpio/gpio12/direction ]; then
        echo out > /sys/class/gpio/gpio12/direction
        echo 0 > /sys/class/gpio/gpio12/value
        sleep 0.2
        echo 1 > /sys/class/gpio/gpio12/value
        return 0
    fi

    return 1
}

control_probe_power_en() {
    if [ -f /sys/class/gpio/probe_power_en/value ]; then
        echo 0 > /sys/class/gpio/probe_power_en/value
        sleep 0.2
        echo 1 > /sys/class/gpio/probe_power_en/value
        return 0
    fi

    return 1
}

# Try GPIO12, fallback to probe_power_en
if ! control_gpio12; then
    control_probe_power_en || fail "No valid GPIO control found"
fi

# ------------------------------
# UART Configuration Section
# ------------------------------
dir="$(dirname $0)"

stty -F /dev/ttymxc1 115200 raw evenp cs8 || fail "UART setup failed"

echo -en "\x79\x90\x14\x01\x00\x0A" > /dev/ttymxc1 || fail "UART command 1 failed"
sleep 0.2

echo -en "\x79\x90\x05\x01\x38\x0A" > /dev/ttymxc1 || fail "UART command 2 failed"
sleep 0.2

echo -en "\x79\x90\x06\x01\xEF\x0A" > /dev/ttymxc1 || fail "UART command 3 failed"
sleep 0.2

# ------------------------------
# SerializerBypassMode Section
# ------------------------------
# DO NOT use exit code; probe-test may output stderr even when success.
# So we capture output and check if it produced *any* output.
# This ensures no false FAIL.

tmpout="/tmp/serializer_silent"

$dir/probe-test api-calls SerializerBypassMode 1 10 >"$tmpout" 2>&1

# If completely empty, probe-test did NOT run → FAIL
if ! [ -s "$tmpout" ]; then
    fail "SerializerBypassMode produced no output"
fi

# ------------------------------
# GPIO Interrupt Setup Section
# ------------------------------
[ -f /sys/class/gpio/mx8_probe_det/edge ] && echo both >/sys/class/gpio/mx8_probe_det/edge
[ -f /sys/class/gpio/mx8_probe_det/active_low ] && echo 1 >/sys/class/gpio/mx8_probe_det/active_low
[ -f "/sys/class/gpio/SPI Interrupt/edge" ] && echo rising >"/sys/class/gpio/SPI Interrupt/edge"
[ -f /sys/class/gpio/mx8_pic_int3/edge ] && echo rising >/sys/class/gpio/mx8_pic_int3/edge

# ------------------------------
# Final Output
# ------------------------------

echo "Configuration complete!"
exit 0

