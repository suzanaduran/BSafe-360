#################################################################
#! /usr/bin/python                                              #
# Author: Suzana Duran Bernardes                                #
# Adapted from Dan Mandle http://dan.mandle.me September 2012   #
# Contributors: Abdullah Kurkcu                                 #
# License: GPL 2.0                                              #
#################################################################

# SETUP PHASE
# Libraries
import RPi.GPIO as GPIO
import os
from gps import *
from time import *
import threading
from contextlib import closing
from datetime import datetime, timedelta
import sqlite3
import time
import traceback
from mpu6050 import mpu6050 as mpu
from getmac import get_mac_address

# INITIALIZATION PHASE
gpsd = None # Seting the global variable
log_rate = 0.5 # 0.5 seconds
os.system('clear') # Clear the terminal (optional)
GPIO.setmode(GPIO.BCM)
range_limit = 5000 # For the ultrasonic sensor range. Set 5000 rather than 400 because high readings can be due materials such as fabrics or trees rather than truly out-of-range.
LOG_FILE = '/connbike.db' # File for storing data and messages
DEBUG = True

mac = get_mac_address(interface="eth0") # Get mac address of the unit
sensor = mpu(0x68, bus=4) # Calling the MPU6050 sensor

TRIG_r = 23 # Trigger GPIO for ultrasonic sensor on the right
ECHO_r = 24 # Echo GPIO for ultrasonic sensor on the right
TRIG_l = 17 # Trigger GPIO for ultrasonic sensor on the left
ECHO_l = 27 # Echo GPIO for ultrasonic sensor on the left

# Setting up the in and out GPIOs of the ultrasonic sensor
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
    global gpsd # Bring the global variable in scope
    gpsd = gps(mode=WATCH_ENABLE) # Calling the GPS
    self.current_value = None
    self.running = True # Setting the thread running to true
 
  def run(self):
    global gpsd
    while gpsp.running:
      gpsd.next() # This will continue to loop and grab EACH set of gpsd info to clear the buffer

def usDistance(TRIG,ECHO):
  GPIO.output(TRIG, False)

  GPIO.output(TRIG, True)
  time.sleep(0.00001)
  GPIO.output(TRIG, False)

  # Get when the timestamps for start and end of ultrasonic sensor pulse
  while GPIO.input(ECHO)==0:
    pulse_start = time.time()

  while GPIO.input(ECHO)==1:
    pulse_end = time.time()

  # Calculating the distance based on the time between 
  pulse_duration = pulse_end - pulse_start
  distance = pulse_duration * 17150
  distance = round(distance, 2)

  if distance>2 and distance < range_limit:
    return distance
  else:
    return 9999999 # Returns an extremely large value to indicate the reading is out-of-range

def to_unicode(obj, encoding='utf-8'):
    # Checks if obj is a unicode string and converts if not
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj

def log(log_type, values):
  # Add a timestamp to the values
  print (values)
  values = (str(mac),) + (str(datetime.now()),) + values
  # Sanitize values for storage
  # values = tuple([to_unicode(x) for x in values])
  # insert values into the database
  values_str = ','.join('?'*len(values))
  print (values)
  print (values_str)
  query = 'INSERT INTO %s VALUES (%s)' % (LOG_TYPES[log_type], values_str)
  cur.execute(query, values)
  conn.commit()

def log_message(level, message): # Define the function for logging a message
    log(0, (MESSAGE_LEVELS[level], message))


def log_gps(latitude, longitude, timeutc, timefix, altitude, eps, epx, epv, ept, speed, climb, track, 
            mode, usreading_r, usreading_l, gyro_x, gyro_y, gyro_z, acce_x, acce_y, acce_z, temp):

    log(1, (latitude, longitude, timeutc, timefix,altitude, eps, epx, epv, ept, speed, climb, track, 
            mode, usreading_r, usreading_l, gyro_x, gyro_y, gyro_z, acce_x, acce_y, acce_z, temp))

conn = sqlite3.connect(LOG_FILE) # Connect to the local database
cur = conn.cursor() # Initiate the local database cursor

# Build the database schema if necessary
cur.execute('CREATE TABLE IF NOT EXISTS gpsreadings (mac TEXT, dtg TEXT, latitude TEXT, longitude TEXT, \
                                                     timeutc TEXT, timefix TEXT, altitude TEXT, \
                                                     eps TEXT, epx TEXT, epv TEXT, ept TEXT, speed TEXT, \
                                                     climb TEXT, track TEXT, mode TEXT, usreading_r TEXT, \
                                                     usreading_l TEXT, gyro_x TEXT, gyro_y TEXT, gyro_z TEXT, \
                                                     acce_x TEXT, acce_y TEXT, acce_z TEXT, temp TEXT)') # Table for sensor data

cur.execute('CREATE TABLE IF NOT EXISTS messages (mac TEXT, dtg TEXT, lvl TEXT, msg TEXT)') # Table for log messages

conn.commit() # Commit new tables

log_message(0, 'GPS module started.') # Create a log message to indicate the GPS has started
gpsp = GpsPoller() # Create the GPS thread
gpsp.start() # Start the GPS up

# Start the sniffer
while True:
  try:
    # PROCESSING PHASE
    # Get the distance readings from the right and left ultrasonic sensors
    usreading_r = usDistance(TRIG_r,ECHO_r)
    usreading_l = usDistance(TRIG_l,ECHO_l)

    # Get the gyroscope vector from the MPU6050
    gyro = sensor.get_gyro_data()
    gyro_x = gyro['x']
    gyro_y = gyro['y']
    gyro_z = gyro['z']
    
    # Get the acceleration vector from the MPU6050
    acce = sensor.get_accel_data()
    acce_x = acce['x']
    acce_y = acce['y']
    acce_z = acce['z']
    
    temp = sensor.get_temp() # Get the temperature from the MPU6050
    
    # STORAGE PHASE
    data = [gpsd.fix.latitude, gpsd.fix.longitude, gpsd.utc, gpsd.fix.time, gpsd.fix.altitude, 
            gpsd.fix.eps, gpsd.fix.epx, gpsd.fix.epv, gpsd.fix.ept, gpsd.fix.speed, gpsd.fix.climb, 
            gpsd.fix.track , gpsd.fix.mode, usreading_r, usreading_l, gyro_x, gyro_y, gyro_z, acce_x, 
            acce_y, acce_z, temp] # Define which variables are gonna be uploaded to the local database

    log_gps(*data) # Upload the data to the local database

    time.sleep(log_rate) # Set to whatever the log_rate is

  # TERMINATION PHASE (INTERRUPTION)
  except KeyboardInterrupt:
    break
  except: # Log a message in case of error
    if DEBUG: print(traceback.format_exc())
    log_message(1, 'Reading error.')
    continue

# TERMINATION PHASE (END OF PROGRAM)
log_message(0, 'Sensor stopped.') # Log message to indicate the sensor data collection has stopped

conn.close() # Close connection to the local database

