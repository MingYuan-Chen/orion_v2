#!/bin/sh

BUS=2
ADDR_HEX="4c"
EXPECTED_HEX="32323232323232323232323232323232"

# 1. Detect EEPROM presence
if ! i2cdetect -y $BUS | grep -qi "\b$ADDR_HEX\b"; then
    echo "EPPROM Test = FAIL"
    echo "1. EEPROM NOT detected on I2C bus $BUS address 0x$ADDR_HEX."
    exit 1
fi

# 2. Read first 16 bytes
TMPFILE=$(mktemp)
eeprog -q -f -8 /dev/i2c-$BUS 0x$ADDR_HEX -r 0x00:16 > "$TMPFILE" 2>/dev/null
RAW_HEX=$(hexdump -v -e '16/1 "%02X"' "$TMPFILE")
rm -f "$TMPFILE"

# Normalize case
RAW_HEX_UPPER=$(echo "$RAW_HEX" | tr 'a-f' 'A-F')

# 3. Check BOTH conditions: detected AND exact hex match
if [ "$RAW_HEX_UPPER" = "$EXPECTED_HEX" ]; then
    echo "EPPROM Test = PASS"
    echo "1. EEPROM detected on I2C bus $BUS address 0x$ADDR_HEX."
    echo "2. Raw HEX = $RAW_HEX_UPPER"
    exit 0
else
    echo "EPPROM Test = FAIL"
    echo "1. EEPROM detected on I2C bus $BUS address 0x$ADDR_HEX."
    echo "2. Raw HEX = $RAW_HEX_UPPER"
    exit 1
fi

