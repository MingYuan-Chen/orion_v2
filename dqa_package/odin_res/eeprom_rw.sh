ret=0
I2CBUS=/dev/i2c-0
EEPROM0=0x55

# Create blob with random data
dd if=/dev/urandom of=to_eeprom0_data bs=1 count=32
dd if=/dev/zero bs=1 count=32 | tr "\000" "\377" > ff_file
sync
to_eeprom0_date_md5=$(md5sum to_eeprom0_data|cut -d" " -f1)

# Test start
cat to_eeprom0_data | eeprog -f -16 $I2CBUS $EEPROM0 -w 0x3fe0
sync
eeprog /dev/i2c-0 $EEPROM0 -16 -f -q -r 0x3fe0:32 > from_eeprom0_data
sync
from_eeprom0_data_md5=$(md5sum from_eeprom0_data|cut -d" " -f1)

echo "$to_eeprom0_date_md5 : $from_eeprom0_data_md5"
if [ "$to_eeprom0_date_md5" != "$from_eeprom0_data_md5" ]; then
    ret=1
fi

#Reset to 0xFF
cat ff_file | eeprog -f -16 $I2CBUS $EEPROM0 -w 0x3fe0
sync

# Restore all
rm -f to_eeprom0_data from_eeprom0_data ff_file
sync

exit $ret

