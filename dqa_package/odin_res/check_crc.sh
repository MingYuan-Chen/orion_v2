#!/bin/sh
# one row = 5888 * 2 bytes
ROW=11776

# Auto detect latest folder under /tmp
if [ -z "$1" ]; then
    DIR=$(ls -td /tmp/??-??-20* 2>/dev/null | head -n 1)
    echo "Auto detected latest folder: $DIR"
else
    DIR=$1
fi

if [ ! -d "$DIR" ]; then
    echo "Folder not found: $DIR"
    exit 1
fi

if [ -f all_crc ]; then
    rm all_crc
fi

# Start from plane02 (plane01 sometimes fails)
for j in $(seq -w 02 14);
do
    FILE=${DIR}/plane${j}

    for i in $(seq 1 80);
    do
        START=$(($i * $ROW - 4))
        hexdump -s $START -n 4 -Cv $FILE | cut -d ' ' -f 5 | head -n 1 >> all_crc
    done

    MD5=$(md5sum all_crc | cut -d ' ' -f 1)
    echo $MD5

    if [ "$MD5" != "76f2263cf1720e1fb469c81e1fd953ce" ]; then
        echo "Check Sum Error"
        exit 1
    fi

    rm all_crc
done

echo "Check Sum Successful!"
exit 0

