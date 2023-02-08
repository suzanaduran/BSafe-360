#################################################################
#! /usr/bin/python                                              #
# Author: Suzana Duran Bernardes                                #
# License: GPL 2.0                                              #
#################################################################

# SETUP PHASE
# Libraries
import os
import csv
import tempfile
import psycopg2
import sqlite3
import logging
from datetime import datetime
from getmac import get_mac_address

# INITIALIZATION PHASE
logging.basicConfig(filename="postgres_log.txt", level=logging.ERROR) # Create log file for debugging

mac = get_mac_address(interface="eth0") # Get mac address of the unit

while True:
    try: 
        time_n = datetime.now() # Get time from the online system
        print(time_n)

        time_rtc = os.popen('sudo hwclock -r').read() # Get time from the RTC 
        print(time_rtc)
        
        os.system('sudo rm /home/pi/connbike_copy.db') # Remove any existing copy of the database
        os.system('sudo cp /connbike.db /home/pi/connbike_copy.db') # Create a copy of the most up-to-date database
    except:
        logging.error("Time or File Exception occurred", exc_info=True) # Log message in case of error
    try:
        try: # Trying to connect to online PostgreSQL database. If no internet is available, it will do nothing
            print('Connecting to the PostgreSQL database...')

            connpg = psycopg2.connect(host='[SERVER_IP]', user='[YOUR_USERNAME]',password='[YOUR_PASSWORD]', dbname='[YOUR_DATABASE_NAME]') # Establishing connection
            cur_pg = connpg.cursor() # Creating cursor

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            logging.error("Connection Exception occurred", exc_info=True) # Log message in case of error

        # Create table in the online database in case it does not exist
        sql0 = '''CREATE TABLE IF NOT EXISTS [SCHEMA].[TABLE_NAME](mac TEXT, dtg TEXT, 
        latitude TEXT, longitude TEXT, timeutc TEXT, timefix TEXT, altitude TEXT, 
        eps TEXT, epx TEXT, epv TEXT, ept TEXT, speed TEXT, climb TEXT, track TEXT,
        mode TEXT, usreading_r TEXT, usreading_l TEXT, gyro_x TEXT, gyro_y TEXT, 
        gyro_z TEXT, acce_x TEXT, acce_y TEXT, acce_z TEXT, temp TEXT,
        CONSTRAINT [TABLE_NAME]_pkey PRIMARY KEY (mac,dtg)) WITH (OIDS = FALSE)TABLESPACE 
        pg_default; GRANT INSERT, SELECT, UPDATE, TRUNCATE, REFERENCES, TRIGGER 
        ON TABLE [SCHEMA].[TABLE_NAME] TO [YOUR_USERNAME];GRANT ALL ON TABLE [SCHEMA].[TABLE_NAME] TO [YOUR_DATBASE_NAME];'''
        cur_pg.execute(sql0)

        connpg.commit() 

        if time_rtc < "2019-01-01 00:00:00.00": # Check for and store data points with erroneous time measured due to outdated RTC
            sql_msg_table = '''CREATE TABLE IF NOT EXISTS [SCHEMA].[TABLE_NAME_MESSAGES](mac TEXT, time_msg, time_rtc, 
            message TEXT,
            CONSTRAINT [TABLE_NAME]_pkey PRIMARY KEY (mac,dtg)) WITH (OIDS = FALSE)TABLESPACE 
            pg_default; GRANT INSERT, SELECT, UPDATE, TRUNCATE, REFERENCES, TRIGGER 
            ON TABLE [SCHEMA].[TABLE_NAME] TO [YOUR_USERNAME];GRANT ALL ON TABLE [SCHEMA].[TABLE_NAME] TO [YOUR_DATBASE_NAME];'''
            cur_pg.execute(sql_msg_table)

            sql_msg_insert ='''INSERT INTO [SCHEMA].[TABLE_NAME_MESSAGES]_messages (mac, time_msg, time_rtc, message) VALUES ({}, {}, {}) 
            ON CONFLICT (mac,dtg) DO NOTHING'''.format(mac,time_n,time_rtc,"RTC OUTDATED")
            cur_pg.execute(sql_msg_insert,)

            connpg.commit()
        else:
            # Create a SQL connection to local SQLite database
            con = sqlite3.connect("/home/pi/connbike_copy.db")
            cur = con.cursor()
            
            # PROCESSING PHASE
            # Check the most recent record in the online database
            sql_pg = ("SELECT mac, dtg FROM [SCHEMA].[TABLE_NAME] WHERE mac = '%s' order by dtg desc limit 1;" % (mac))
            cur_pg.execute(sql_pg)
            latest_pg = cur_pg.fetchall() # Save record in a new variable

            print(latest_pg)

            cur.execute("SELECT * FROM gpsreadings where mac = '%s' and dtg > '%s' order by dtg asc;" % (mac,latest_pg[0][1])) # Get all the values for the unit that were collected after the most recent record stored in the online database
            data = cur.fetchall() # Save the most recent local data in a new variable
            
            # STORAGE PHASE
            if data is None: # Check if there was any data collected after the most recent record stored online
                continue
            else:
                fp = tempfile.NamedTemporaryFile(delete=False) # Create a temporary file

                try:
                    with open(fp.name, 'a+') as f: # Write updated data to temporary csv file
                        writer = csv.writer(f)
                        columns = cur.description 
                        writer.writerow([columns[i][0] for i in range(len(data[0]))])
                        writer.writerows(data)
                    
                    fp.seek(0)

                    cur_pg.copy_expert("COPY [SCHEMA].[TABLE_NAME] FROM STDIN CSV HEADER",fp) # Uploaded values stored in the temporary csv file to online database
                        
                    connpg.commit()

                # TERMINATION PHASE
                except:
                    con.close() 
                    cur_pg.close()
                    continue
                finally:
                    # Close and unlink temporary file
                    fp.close()
                    os.unlink(fp.name)

        # Be sure to close the connection
        con.close()
        cur_pg.close()

    except KeyboardInterrupt: 
        con.close()
        cur_pg.close()
        break
    except:
        pass