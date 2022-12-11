#! /usr/bin/python
# Written by Dan Mandle http://dan.mandle.me September 2012
# License: GPL 2.0
import RPi.GPIO as GPIO
import os
from gps import *
from time import *
import threading
from contextlib import closing
from datetime import datetime, timedelta
import sqlite3
from sqlite3 import Error
import time
import traceback
from config import *
from alerts import *
from mpu6050 import mpu6050 as mpu
from getmac import get_mac_address

gpsd = None #seting the global variable
log_rate = 0.5 # 1 second
os.system('clear') #clear the terminal (optional)
GPIO.setmode(GPIO.BCM)
range_limit = 5000 #for the ultrasonic sensor range
LOG_FILE = '/connbike_test.db'
DEBUG = True

mac = get_mac_address(interface="eth0")
sensor = mpu(0x68, bus=0)

TRIG_r = 23 
ECHO_r = 24
TRIG_l = 17 
ECHO_l = 27

GPIO.setup(TRIG_r,GPIO.OUT)
GPIO.setup(ECHO_r,GPIO.IN) 
GPIO.setup(TRIG_l,GPIO.OUT)
GPIO.setup(ECHO_l,GPIO.IN) 

regist = 0

LOG_TYPES = {
    0: 'messages',
    1: 'gpsreadings',
    2: 'usreadings_r',
    3: 'usreadings_l'
}

MESSAGE_LEVELS = {
    0: 'INFO',
    1: 'ERROR',
    2: 'ALERT',
}

class GpsPoller(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    global gpsd #bring it in scope
    gpsd = gps(mode=WATCH_ENABLE) #starting the stream of info
    self.current_value = None
    self.running = True #setting the thread running to true
 
  def run(self):
    global gpsd
    while gpsp.running:
      gpsd.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer

def usDistance(TRIG,ECHO):
  GPIO.output(TRIG, False)

  GPIO.output(TRIG, True)
  time.sleep(0.00001)
  GPIO.output(TRIG, False)

  while GPIO.input(ECHO)==0:
    pulse_start = time.time()

  while GPIO.input(ECHO)==1:
    pulse_end = time.time()

  pulse_duration = pulse_end - pulse_start
  distance = pulse_duration * 17150
  distance = round(distance, 2)

  if distance>2 and distance < range_limit:
    return distance
  else:
    return "Out of range"

def to_unicode(obj, encoding='utf-8'):
    # checks if obj is a unicode string and converts if not
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj

def log(log_type, values):
  # add a timestamp to the values
  print (values)
  values = (str(mac),) + (str(datetime.now()),) + values
  # sanitize values for storage
  #values = tuple([to_unicode(x) for x in values])
  # insert values into the database
  values_str = ','.join('?'*len(values))
  print (values)
  print (values_str)
  query = 'INSERT INTO %s VALUES (%s)' % (LOG_TYPES[log_type], values_str)
  cur.execute(query, values)
  conn.commit()

def log_message(level, message):
    log(0, (MESSAGE_LEVELS[level], message))


def log_gps(latitude, longitude, timeutc, timefix, altitude, eps, epx, epv, ept, speed, climb, track, 
            mode, usreading_r, usreading_l, gyro_x, gyro_y, gyro_z, acce_x, acce_y, acce_z, temp):
    #oui = resolve_oui(bssid)
    log(1, (latitude, longitude, timeutc, timefix,altitude, eps, epx, epv, ept, speed, climb, track, 
            mode, usreading_r, usreading_l, gyro_x, gyro_y, gyro_z, acce_x, acce_y, acce_z, temp))

conn = sqlite3.connect(LOG_FILE)
cur = conn.cursor()
# build the database schema if necessary
cur.execute('CREATE TABLE IF NOT EXISTS gpsreadings (mac TEXT, dtg TEXT, latitude TEXT, longitude TEXT, \
                                                     timeutc TEXT, timefix TEXT, altitude TEXT, \
                                                     eps TEXT, epx TEXT, epv TEXT, ept TEXT, speed TEXT, \
                                                     climb TEXT, track TEXT, mode TEXT, usreading_r TEXT, \
                                                     usreading_l TEXT, gyro_x TEXT, gyro_y TEXT, gyro_z TEXT, \
                                                     acce_x TEXT, acce_y TEXT, acce_z TEXT, temp TEXT)')
#cur.execute('CREATE TABLE IF NOT EXISTS usreadings (dtg TEXT, cm TEXT)')
cur.execute('CREATE TABLE IF NOT EXISTS messages (mac TEXT, dtg TEXT, lvl TEXT, msg TEXT)')

conn.commit()
log_message(0, 'GPS module started.')
gpsp = GpsPoller() # create the thread
gpsp.start() # start it up

# start the sniffer
while True:
  try:
    usreading_r = usDistance(TRIG_r,ECHO_r)
    usreading_l = usDistance(TRIG_l,ECHO_l)

    gyro = sensor.get_gyro_data()
    gyro_x = gyro['x']
    gyro_y = gyro['y']
    gyro_z = gyro['z']
    
    acce = sensor.get_accel_data()
    acce_x = acce['x']
    acce_y = acce['y']
    acce_z = acce['z']
    
    temp = sensor.get_temp()
    
    data = [gpsd.fix.latitude, gpsd.fix.longitude, gpsd.utc, gpsd.fix.time, gpsd.fix.altitude, 
            gpsd.fix.eps, gpsd.fix.epx, gpsd.fix.epv, gpsd.fix.ept, gpsd.fix.speed, gpsd.fix.climb, 
            gpsd.fix.track , gpsd.fix.mode, usreading_r, usreading_l, gyro_x, gyro_y, gyro_z, acce_x, 
            acce_y, acce_z, temp]
    log_gps(*data)
    time.sleep(log_rate) #set to whatever
  except KeyboardInterrupt:
    break
  except:
    if DEBUG: print(traceback.format_exc())
    log_message(1, 'Reading error.')
    continue
log_message(0, 'Sensor stopped.')
conn.close()

