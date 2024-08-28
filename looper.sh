#! /usr/bin/sh
while true; do
    echo fired `date +'%Y-%M-%d %H:%M:%S'`
    bash "pushgateway-transporter.sh" $@
    sleep 1
done;