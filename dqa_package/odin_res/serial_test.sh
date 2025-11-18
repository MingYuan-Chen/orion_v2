#dd if=/dev/urandom of=/tmp/test_file count=20 2>/dev/null
string=`cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w ${1:-32} | head -n 1`
echo -n > /tmp/test_file
echo $string >> /tmp/test_file

sum=`md5sum /tmp/test_file | awk -e '{ print $1 }'`

port=$1

ret=0

stty -F $port 115200 raw -echo
echo -n > $port
sleep 1
cat $port > /tmp/test_read &
cat /tmp/test_file > $port
pid=`echo $!`
sleep 3
kill $pid
sum_new=`md5sum /tmp/test_read | awk -e '{ print $1 }'`
if [ $sum != $sum_new ]; then
	ret=1
	echo "Loopback test for $port FAILED!!"
else
	echo "Loopback test for $port PASSED!!"
fi

exit $ret
