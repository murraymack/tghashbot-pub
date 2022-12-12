#!/usr/bin/env bash

# Script to keep api.py running upon crash

while true
do

PIDCHECK=$( ps -ef | grep -oE "[[:digit:]] python3 /home/ssm-user/imperiumhashbot/api.py" | wc -l )

if [[ $PIDCHECK -eq 1 ]]
        then
                echo $(date) "api alive"
fi


if [[ $PIDCHECK -eq 0 ]]
        then
                echo $(date) "Restarting api.py" >> /home/ssm-user/imperiumhashbot/keepalive.log
                nohup /home/ssm-user/imperiumhashbot/api.py &
fi

sleep 15

done