#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Work in progress...


import sys
import datetime
import schedule
import time
from dateutil.relativedelta import relativedelta
import logging

import mqtt
import standalone
import hass
import param
import database
import influxdb # outcommented as throwing error if not using influx (missing influxclient)
import traceback


# gazpar2mqtt constants
P2M_VERSION = '0.1.0'
P2M_DB_VERSION = '0.1.0'
P2M_INFLUXDB_VERSION = '0.1.0'

#######################################################################
#### Functions
#######################################################################

# Sub to get date with year offset
def _getYearOfssetDate(day, number):
    return day - relativedelta(years=number)

# Sub to return format wanted
def _dateTimeToStr(datetime):
    return datetime.strftime("%d/%m/%Y - %H:%M:%S")

########################################################################################################################
#### Running program
########################################################################################################################
def run(myParams):

    myMqtt = None
    myPronote = None

    # Store time now
    dtn = _dateTimeToStr(datetime.datetime.now())


    # STEP 1 : Connect to database
    ####################################################################################################################
    logging.info("-----------------------------------------------------------")
    logging.info("#        Connexion to SQLite database                     #")
    logging.info("-----------------------------------------------------------")

    # Create/Update database
    logging.info("Connexion to SQLite database...")
    myDb = database.Database(myParams.dbPath)


    # Connect to database
    myDb.connect(P2M_VERSION,P2M_DB_VERSION,P2M_INFLUXDB_VERSION)
    if myDb.isConnected() :
        logging.info("SQLite database connected !")
    else:
        logging.error("Unable to connect to SQLite database.")

    # Check program version
    p2mVersion = myDb.getConfig(database.P2M_KEY)
    p2mDate = myDb.getConfig(database.LAST_EXEC_KEY)
    logging.info("Last execution date %s, program was in version %s.",p2mDate,p2mVersion)
    if p2mVersion != P2M_VERSION:
        logging.warning("pronote2mqtt version (%s) has changed since last execution (%s)",P2M_VERSION,p2mVersion)
        # Update program version
        myDb.updateVersion(database.P2M_KEY,P2M_VERSION)
        myDb.commit()


    # Reinit database when required :
    if myParams.dbInit:
        logging.info("Reinitialization of the database...")
        myDb.reInit(P2M_VERSION,P2M_DB_VERSION,P2M_INFLUXDB_VERSION)
        logging.info("Database reinitialized to version %s",P2M_DB_VERSION)
    else:
        # Compare dabase version
        logging.info("Checking database version...")
        dbVersion = myDb.getConfig(database.DB_KEY)
        if dbVersion == P2M_DB_VERSION:
            logging.info("Your database is already up to date : version %s.",P2M_DB_VERSION)

            # Display current database statistics
            logging.info("Retrieve database statistics...")
            #dbStats = myDb.getPeriodsCount(pronote.TYPE)
            logging.info("%s informatives periods stored", dbStats["rows"])
            logging.info("%s Periods(s)", dbStats["pid"])
            logging.info("First period : %s", dbStats["minDate"])
            logging.info("Last period : %s", dbStats["maxDate"])

        else:
            logging.warning("Your database (version %s) is not up to date.",dbVersion)
            logging.info("Reinitialization of your database to version %s...",P2M_DB_VERSION)
            myDb.reInit(P2M_VERSION,P2M_DB_VERSION,P2M_INFLUXDB_VERSION)
            dbVersion = myDb.getConfig(database.DB_KEY)
            logging.info("Database reinitialized to version %s !",dbVersion)
   
    



    ####################################################################################################################
    # STEP 7 : Disconnect from database
    ####################################################################################################################
    logging.info("-----------------------------------------------------------")
    logging.info("#          Disconnexion from SQLite database              #")
    logging.info("-----------------------------------------------------------")

    if myDb.isConnected() :
        myDb.close()
        logging.info("SQLite database disconnected")
    del myDb

    ####################################################################################################################
    # STEP 8 : Display next run info and end of program
    ####################################################################################################################
    logging.info("-----------------------------------------------------------")
    logging.info("#                Next run                                 #")
    logging.info("-----------------------------------------------------------")
    if myParams.scheduleTime is not None:
        logging.info("gazpar2mqtt next run scheduled at %s",myParams.scheduleTime)
    else:
        logging.info("No schedule defined.")


    logging.info("-----------------------------------------------------------")
    logging.info("#                  End of program                         #")
    logging.info("-----------------------------------------------------------")



########################################################################################################################
#### Main
########################################################################################################################
if __name__ == "__main__":
    
    # Load params
    myParams = param.Params()
        
    # Set logging
    if myParams.debug:
        myLevel = logging.DEBUG
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=myLevel)
    else:
        myLevel = logging.INFO
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=myLevel)
    
    
    # Say welcome and be nice
    logging.info("-----------------------------------------------------------")
    logging.info("#               Welcome to gazpar2mqtt                    #")
    logging.info("-----------------------------------------------------------")
    logging.info("Program version : %s",G2M_VERSION)
    logging.info("Database version : %s", G2M_DB_VERSION)
    logging.info("Influxdb version : %s", G2M_INFLUXDB_VERSION)
    logging.info("Please note that the the tool is still under development, various functions may disappear or be modified.")
    logging.debug("If you can read this line, you are in DEBUG mode.")
    
    # Log params info
    logging.info("-----------------------------------------------------------")
    logging.info("#                Program parameters                       #")
    logging.info("-----------------------------------------------------------")
    myParams.logParams()
    
    # Check params
    logging.info("Check parameters...")
    if myParams.checkParams():
        logging.info("Parameters are ok !")
    else:
        logging.error("Error on parameters. End of program.")
        quit()

    
    # Run
    if myParams.scheduleTime is not None:
        
        # Run once at lauch
        run(myParams)

        # Then run at scheduled time
        schedule.every().day.at(myParams.scheduleTime).do(run,myParams)
        while True:
            schedule.run_pending()
            time.sleep(1)
        
    else:
        
        # Run once
        run(myParams)
        logging.info("End of gazpar2mqtt. See u...")