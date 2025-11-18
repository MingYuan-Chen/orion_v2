if [ "$#" != 1 ]; then
    echo "Wrong parameter!!"
    echo "wifienable.sh [ssid_name]"
    exit 1
fi
WIFI_SSID=$1

/usr/bin/res/wifi_connect.sh $WIFI_SSID

if ["$?" != "0"]; then
    echo "Connect to $WIFI_SSID fail"
        exit 1
fi

R=`date '+%S'`
if [ $R == "00" ] || [ $R == "01" ];then
    R=2
fi

ifconfig wlan0 192.168.1.$R
route add default gw 192.168.1.1

exit 0
