#/bin/bash
# v1.3 2020.11.08.

export PYTHONPATH="/home/pi/import"

while true; do
    pkill task01.py
    ~/rpi_station/task01.py & >/dev/null 2>&1 
    sleep 600
done


