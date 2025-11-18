ntpdate 192.168.1.254
if [ $? == 0 ]; then
  exit 0
fi
exit 1
