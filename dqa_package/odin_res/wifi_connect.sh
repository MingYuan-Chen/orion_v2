#!/bin/sh

SSID=$1

ifconfig wlan0 up

sleep 1

connmanctl disable wifi
connmanctl enable wifi
sleep 1
##connmanctl scan wifi
SERVICE=`connmanctl services | grep $SSID | head -n 1 | cut -d 'w' -f 2`

echo $SERVICE
if [ ! "$SERVICE" ];then
    echo "sleep and try again."
    sleep 1
    SERVICE=`connmanctl services | grep $SSID | head -n 1 | cut -d 'w' -f 2`
    
    if [ ! "$SERVICE" ];then
        echo "still fail."
        exit 1
    fi
fi

CON=w$SERVICE

echo $CON

connmanctl disconnect $CON
sleep 1

ret=`connmanctl connect $CON | grep Connected | wc -l`

if [ "$ret" = "1" ]; then
        echo "connect success"
        exit 0
else
        echo "connect fail"
        exit 1
fi

