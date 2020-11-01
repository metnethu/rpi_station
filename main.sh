#/bin/bash

while true; do
    pkill task01.py
    /home/pi/rpi_station/task01.py &
    sleep 600
done

# Ha ez megjelenik, akkor működik az automatikus github
