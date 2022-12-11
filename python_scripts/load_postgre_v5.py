import os
import csv
import tempfile
import psycopg2
import sqlite3
import logging
from datetime import datetime
from getmac import get_mac_address

logging.basicConfig(filename="postgres_log.txt", level=logging.ERROR)

mac = get_mac_address(interface="eth0")

while True:
    try:
        time_n = datetime.now();
        print(time_n)

        time_rtc = os.popen('sudo hwclock -r').read()
        print(time_rtc)
        
        os.system('sudo rm /home/pi/connbike_copy.db')
        os.system('sudo cp /connbike_test.db /home/pi/connbike_copy.db')
    except:
        logging.error("Time or File Exception occurred", exc_info=True)
    try:
        try:
            print('Connecting to the PostgreSQL database...')

            connpg = psycopg2.connect(host='[SERVER_IP]', user='[YOUR_USERNAME]',password='[YOUR_PASSWORD]', dbname='[YOUR_DATABASE_NAME]')
            cur_pg = connpg.cursor()
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            logging.error("Connection Exception occurred", exc_info=True)
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

        if time_rtc < "2019-01-01 00:00:00.00":
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
            # Create a SQL connection to our SQLite database
            con = sqlite3.connect("/home/pi/connbike_copy.db")
            cur = con.cursor()

            sql_pg = ("SELECT mac,dtg FROM [SCHEMA].[TABLE_NAME]order by dtg desc limit 1;")
            cur_pg.execute(sql_pg)
            latest_pg = cur_pg.fetchall()

            print(latest_pg)

            cur.execute("SELECT * FROM gpsreadings where mac = '%s' and dtg > '%s' order by dtg asc;" % (latest_pg[0][0],latest_pg[0][1]))
            data = cur.fetchall()

            if data is None:
                continue
            else:
                fp = tempfile.NamedTemporaryFile(delete=False)

                try:
                    with open(fp.name, 'a+') as f:
                        writer = csv.writer(f)
                        columns = cur.description 
                        writer.writerow([columns[i][0] for i in range(len(data[0]))])
                        writer.writerows(data)
                    
                    fp.seek(0)

                    cur_pg.copy_expert("COPY [SCHEMA].[TABLE_NAME] FROM STDIN CSV HEADER",fp)
                        
                    connpg.commit()
                except:
                    con.close()
                    cur_pg.close()
                    continue
                finally:
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