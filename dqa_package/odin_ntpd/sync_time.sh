#!/bin/bash

SERVER="192.168.6.11"
TMP="/tmp/ntp_sync.$$"

> "$TMP"

##############
# Run ntpdate and capture raw output
##############
RAW=$(ntpdate -u "$SERVER" 2>&1)
echo "$RAW" | tee "$TMP"

##############
# Determine PASS / FAIL
##############

if echo "$RAW" | grep -qi "adjust time server"; then
    RESULT="PASS"
else
    RESULT="FAIL"
fi

##############
# Print date and hwclock
##############
date
hwclock -r

##############
# Final result (print at bottom)
##############
echo "Sync Time = $RESULT"

rm -f "$TMP"

