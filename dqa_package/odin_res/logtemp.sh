#!/bin/sh

name=$(date '+%Y-%m-%d-%H-%M-%S')

while true
do
date=$(date '+%Y-%m-%d %H:%M:%S')
temp=`cat /sys/class/thermal/thermal_zone0/temp`
load=`uptime | cut -d 'l' -f 2 | cut -d ':' -f 2 | cut -d ',' -f 1`
load4=`awk "BEGIN {print $load*25}"`
cpu0=`cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_cur_freq`
cpu1=`cat /sys/devices/system/cpu/cpu1/cpufreq/cpuinfo_cur_freq`
cpu2=`cat /sys/devices/system/cpu/cpu2/cpufreq/cpuinfo_cur_freq`
cpu3=`cat /sys/devices/system/cpu/cpu3/cpufreq/cpuinfo_cur_freq`

echo -e "$date\t$load4\t$cpu0\t$cpu1\t$cpu2\t$cpu3\t$temp" >> ~/temp-$name.log

sleep 5
done

exit 0
