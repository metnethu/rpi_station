#/bin/bash
# v1.1
# 2020.11.08.

export PYTHONPATH="/home/pi/import"

while true; do
    pkill task01.py
    /home/pi/rpi_station/task01.py &
    sleep 600
done

