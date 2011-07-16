#!/bin/bash

if [ $# -ne 3 ]
then
  echo "Usage: `basename $0` port <speed-limit-in-kbps] [packet-loss]"
  exit $E_BADARGS
fi

hexport=$(echo "obase=16; $1" | bc)
netem_loss_handle="$12"

# Add main classes 
/sbin/tc qdisc add dev lo root handle 1: htb
/sbin/tc class add dev lo parent 1: classid 1:1 htb rate 1000000kbps


echo "------- Remove any previous rule"
# Delete any old rules (if rules are missing , failure in these commands can be expected)
/sbin/tc qdisc del dev lo parent 1:$hexport handle $netem_loss_handle
/sbin/tc filter del dev lo parent 1:0 prio $1 protocol ip handle $1 fw flowid 1:$hexport
/sbin/tc class del dev lo parent 1:1 classid 1:$hexport
/sbin/iptables -D OUTPUT -t mangle -p tcp --sport $1 -j MARK --set-mark $1

echo "------- Adding rule"
# Add the new rule 
/sbin/tc class add dev lo parent 1:1 classid 1:$hexport htb rate $2kbps ceil $2kbps prio $1
/sbin/tc filter add dev lo parent 1:0 prio $1 protocol ip handle $1 fw flowid 1:$hexport
/sbin/tc qdisc add dev lo parent 1:$hexport handle $netem_loss_handle: netem loss $3%
/sbin/iptables -A OUTPUT -t mangle -p tcp --sport $1 -j MARK --set-mark $1

