#!/bin/sh

BUS=2
ADDR_HEX="4c"

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

# Extract first 6 HEX (first 3 bytes)
PREFIX=${RAW_HEX_UPPER:0:6}

# 3. Check first 6 HEX = 323232
if [ "$PREFIX" = "323232" ]; then
    echo "EPPROM Test = PASS"
    echo "1. EEPROM detected on I2C bus $BUS address 0x$ADDR_HEX."
    echo "2. Raw HEX = $RAW_HEX_UPPER"
    echo "3. First 6 HEX matched: $PREFIX"
    exit 0
else
    echo "EPPROM Test = FAIL"
    echo "1. EEPROM detected on I2C bus $BUS address 0x$ADDR_HEX."
    echo "2. Raw HEX = $RAW_HEX_UPPER"
    echo "3. First 6 HEX mismatch (got $PREFIX, expected 323232)"
    exit 1
fi

