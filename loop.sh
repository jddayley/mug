#!/bin/bash
#export BLEAK_LOGGING=1
x=1
s=1

while [ $s -le 5 ]
 do
   echo "# of Mug $x samples"
#   hciconfig hci0 down && hciconfig hci0 up
   sleep 2 
   x=$(( $x + 1 ))
   python3 ble.py
   sleep 5
done
