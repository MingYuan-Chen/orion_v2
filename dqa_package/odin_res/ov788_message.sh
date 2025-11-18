port=$1
power=$2
ret=0

stty -F $port 115200 raw -echo
echo -n > $port
sleep 1
cat $port > /tmp/ov788_debug_read &
pid=`echo $!`
echo 0 > $power
sleep 1
echo 1 > $power
sleep 1
kill $pid
result=`cat /tmp/ov788_debug_read | grep version`
if [ $? != 0 ]; then
        ret=1
        echo "ov788 debug message test for $port FAILED!!"
else
        echo "ov788 debug message test for $port PASSED!!"
fi

exit $ret
