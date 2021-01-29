#!/usr/bin/python -u
# coding=utf-8
# "DATASHEET": http://cl.ly/ekot
# https://gist.github.com/kadamski/92653913a53baf9dd1a8
# V1.22 2020.11.28

from __future__ import print_function
import serial, struct, sys, time, subprocess, requests, bme280, Adafruit_DHT, math

try:
    import gpio
except:
    print("No GPIO avaiable...")

DEBUG = 0
CMD_MODE = 2
CMD_QUERY_DATA = 4
CMD_DEVICE_ID = 5
CMD_SLEEP = 6
CMD_FIRMWARE = 7
CMD_WORKING_PERIOD = 8
MODE_ACTIVE = 0
MODE_QUERY = 1
PERIOD_CONTINUOUS = 0



def dump(d, prefix=''):
    print(prefix + ' '.join(x.encode('hex') for x in d))

def construct_command(cmd, data=[]):
    assert len(data) <= 12
    data += [0,]*(12-len(data))
    checksum = (sum(data)+cmd-2)%256
    ret = "\xaa\xb4" + chr(cmd)
    ret += ''.join(chr(x) for x in data)
    ret += "\xff\xff" + chr(checksum) + "\xab"

    if DEBUG:
        dump(ret, '> ')
    return ret

def process_data(d):
    r = struct.unpack('<HHxxBB', d[2:])
    pm25 = r[0]/10.0
    pm10 = r[1]/10.0
    checksum = sum(ord(v) for v in d[2:8])%256
    return [pm25, pm10]
    #print("PM 2.5: {} μg/m^3  PM 10: {} μg/m^3 CRC={}".format(pm25, pm10, "OK" if (checksum==r[2] and r[3]==0xab) else "NOK"))

def process_version(d):
    r = struct.unpack('<BBBHBB', d[3:])
    checksum = sum(ord(v) for v in d[2:8])%256
    print("Y: {}, M: {}, D: {}, ID: {}, CRC={}".format(r[0], r[1], r[2], hex(r[3]), "OK" if (checksum==r[4] and r[5]==0xab) else "NOK"))

def read_response():
    byte = 0
    while byte != "\xaa":
        byte = ser.read(size=1)

    d = ser.read(size=9)

    if DEBUG:
        dump(d, '< ')
    return byte + d

def cmd_set_mode(mode=MODE_QUERY):
    ser.write(construct_command(CMD_MODE, [0x1, mode]))
    read_response()

def cmd_query_data():
    ser.write(construct_command(CMD_QUERY_DATA))
    d = read_response()
    values = []
    if d[1] == "\xc0":
        values = process_data(d)
    return values

def cmd_set_sleep(sleep):
    mode = 0 if sleep else 1
    print ("Mode: "+str(mode))
    ser.write(construct_command(CMD_SLEEP, [0x1, mode]))
    read_response()

def cmd_set_alive(sleep):
    mode = 0 if sleep else 1
    ser.write(construct_command(CMD_SLEEP, [0x1, mode]))
    read_response()

def cmd_set_working_period(period):
    ser.write(construct_command(CMD_WORKING_PERIOD, [0x1, period]))
    read_response()

def cmd_firmware_ver():
    ser.write(construct_command(CMD_FIRMWARE))
    d = read_response()
    process_version(d)

def cmd_set_id(id):
    id_h = (id>>8) % 256
    id_l = id % 256
    ser.write(construct_command(CMD_DEVICE_ID, [0]*10+[id_l, id_h]))
    read_response()

def pub_mqtt(jsonrow):
    cmd = ['mosquitto_pub', '-h', MQTT_HOST, '-t', MQTT_TOPIC, '-s']
    print('Publishing using:', cmd)
    with subprocess.Popen(cmd, shell=False, bufsize=0, stdin=subprocess.PIPE).stdin as f:
        json.dump(jsonrow, f)

def rhcode(p1):
  if (p1==0):
    return(-999)
  else:
    return(p1)

def Z_filter(cucc):
  res = list()
  l2 = list()
  sum = 0
  dev = 0
  c = 0
  for p in cucc:
    if ((p<>-999) and (p<>None)):
      l2.append(p)
      sum=sum+p
      c=c+1
  if (c==0):
    return('')
  mean=sum/c
  for o in l2:
    dev=dev+pow(o-mean,2)
  dev=math.sqrt(dev)/c
  print("mean:", mean, "dev:", dev)
  sum = 0
  c   = 0
  for o in l2:
    if ((mean-o)<=3*dev):
      c=c+1
      sum=sum+o
    else:
      print("Kidobom: ",o)
  if (c==0):
    return('')
  else:
    return(round(sum/c,1))
        
key = open("/boot/key","r").read()
key = key[:-1]

try:
    gpio.setmode(gpio.BCM)
    gpio.setup(17, gpio.OUT, initial=gpio.LOW)
    gpio.output(17, gpio.HIGH)
except:
    print("GPIO hiba...")

if __name__ == "__main__":
#    while True:
        try:
            ser = serial.Serial()
            ser.port = "/dev/ttyUSB0"
            ser.baudrate = 9600
            ser.open()
            ser.flushInput()
            byte, data = 0, ""
            cmd_set_sleep(0)
            cmd_firmware_ver()
            cmd_set_working_period(PERIOD_CONTINUOUS)
            cmd_set_mode(MODE_QUERY);
            pm25=list()
            pm10=list()
            for t in range(15):
                values = cmd_query_data();
                if values is not None and len(values) == 2:
                  print("PM2.5: ", values[0], ", PM10: ", values[1], "for dummy")
                  time.sleep(2)
            for t in range(15):
                values = cmd_query_data();
                if values is not None and len(values) == 2:
                  print("PM2.5: ", values[0], ", PM10: ", values[1])
                  time.sleep(2)
                  pm25.append(values[0])
                  pm10.append(values[1])
            print(*pm25)
            print(*pm10)
            post_data = {'pm2' : round(sum(pm25)/len(pm25)), 'pm10' : round(sum(pm10)/len(pm10)), 'date' : time.time()}
        except:
            post_data = {'date' : time.time()}

        t = list()
        p = list()
        rh = list()
        for i in range(0,15):
          try:
            t1,p1,rh1 = bme280.readBME280All()
          except:
            t1,p1,rh1 = (-999, -999, -999)
          t.append(t1)
          p.append(p1)
          rh.append(rhcode(rh1))
          time.sleep(1)
        for i in range(0,3):
          try:
            rh1, t1 = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, 4)
            print("DHT: ",t1,rh1)
          except:
            rh1, t1 = (-999, -999)
            try:
              gpio.output(17, gpio.LOW)
              time.sleep(1)
              gpio.output(17, gpio.HIGH)
            except:
              print("GPIO hiba...")
          t.append(t1)
          rh.append(rhcode(rh1))
        
        tz=Z_filter(t)
        pz=Z_filter(p)
        rhz=Z_filter(rh)

        print ("Temperature : ", tz, "C")
        print ("Humidity : ", rhz, "%")
        print ("Pressure : ", pz, "hPa")

        if (pz<>''):
          post_data['pressure']=pz
        if (tz<>''):
          post_data['temperature']=tz
        if (rhz<>''):
          post_data['humidity']=rhz

        response = requests.post('https://www.metnet.hu/api/data', data = post_data, headers={'x-device-token': key})
        print(post_data)
        print(response.text)
        try:
            cmd_set_sleep(1)
            ser.close()
        except:
            time.sleep(1)
        try:
          gpio.output(17, gpio.LOW)
        except:
          print("GPIO hiba...")
