#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Work in progress...


import sys
import datetime
import schedule
import time
from dateutil.relativedelta import relativedelta
import logging

#import pronote
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

# Sub to wait between 2 PRONOTE tries
def _waitBeforeRetry(tryCount):
    waitTime = round(pronote._getRetryTimeSleep(tryCount))
    if waitTime < 200:
        logging.info("Wait %s seconds (%s min) before next try",waitTime,round(waitTime/60))
    else:
        logging.info("Wait %s minutes before next try",round(waitTime/60))
    time.sleep(waitTime)

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
            dbStats = myDb.getPeriodsCount(pronote.TYPE)
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
   
    
    # STEP 2 : Log to MQTT broker
    ####################################################################################################################
    logging.info("-----------------------------------------------------------")
    logging.info("#              Connexion to Pronote Client                #")
    logging.info("-----------------------------------------------------------")

    try:

        logging.info("Connect to Mqtt broker...")

        # Create mqtt client
        myMqtt = mqtt.Mqtt(myParams.mqttClientId,myParams.mqttUsername,myParams.mqttPassword,myParams.mqttSsl,myParams.mqttQos,myParams.mqttRetain)

        # Connect mqtt broker
        myMqtt.connect(myParams.mqttHost,myParams.mqttPort)

        # Wait for connexion callback
        time.sleep(2)

        if myMqtt.isConnected:
            logging.info("Mqtt broker connected !")

    except:
        logging.error("Unable to connect to Mqtt broker. Please check that broker is running, or check broker configuration.")



    # STEP 3 : Get data from GRDF website
    ####################################################################################################################
    if myMqtt.isConnected:

        logging.info("-----------------------------------------------------------")
        logging.info("#            Get data from PRONOTE website                   #")
        logging.info("-----------------------------------------------------------")

        tryCount = 0
        # Connexion
        while tryCount < gazpar.GRDF_API_MAX_RETRIES :
            try:

                tryCount += 1

                # Create Grdf instance
                logging.info("Connexion to GRDF, try %s/%s...",tryCount,gazpar.GRDF_API_MAX_RETRIES)
                myGrdf = gazpar.Grdf()

                # Connect to Grdf website
                myGrdf.login(myParams.grdfUsername,myParams.grdfPassword)

                # Check connexion
                if myGrdf.isConnected:
                    logging.info("GRDF connected !")
                    break
                else:
                    logging.info("Unable to login to GRDF website")
                    _waitBeforeRetry(tryCount)

            except:
                myGrdf.isConnected = False
                logging.info("Unable to login to GRDF website")
                _waitBeforeRetry(tryCount)


        # When GRDF is connected
        if myGrdf.isConnected:

            # Sub-step 3A : Get account info
            try:

                # Get account informations and store it to db
                logging.info("Retrieve account informations")
                myAccount = myGrdf.getWhoami()
                myAccount.store(myDb)
                myDb.commit()

            except:
                logging.warning("Unable to get account information from GRDF website.")


            # Sub-step 3B : Get list of PCE
            logging.info("Retrieve list of PCEs...")
            try:
                myGrdf.getPceList()
                logging.info("%s PCE found !",myGrdf.countPce())
            except:
                myGrdf.isConnected = False
                logging.info("Unable to get any PCE !")

            # Loop on PCE
            if myGrdf.pceList:
                for myPce in myGrdf.pceList:

                    # Store PCE in database
                    myPce.store(myDb)
                    myDb.commit()


                    # Sub-step 3C : Get measures of the PCE

                    # Get measures of the PCE
                    logging.info("---------------------------------")
                    logging.info("Get measures of PCE %s alias %s",myPce.pceId,myPce.alias)


                    # Set date range
                    minDateTime = _getYearOfssetDate(datetime.datetime.now(), 3) # GRDF min date is 3 years ago
                    startDate = minDateTime.date()
                    endDate = datetime.date.today()
                    logging.info("Range period : from %s (3 years ago) to %s (today) ...",startDate,endDate)

                    # Get informative measures
                    logging.info("---------------")
                    logging.info("Retrieve informative measures...")
                    try:
                        myGrdf.getPceMeasures(myPce,startDate,endDate,gazpar.TYPE_I)
                        logging.info("Informative measures found !")
                    except:
                        logging.error("Error during informative measures collection")


                    # Analyse data
                    measureCount = myPce.countMeasure(gazpar.TYPE_I)
                    if measureCount > 0:
                        logging.info("Analysis of informative measures provided by GRDF...")
                        logging.info("%s informative measures provided by Grdf", measureCount)
                        measureOkCount = myPce.countMeasureOk(gazpar.TYPE_I)
                        logging.info("%s informative measures are ok", measureOkCount)
                        accuracy = round((measureOkCount/measureCount)*100)
                        logging.info("Accuracy is %s percent",accuracy)

                        # Get last informative measure
                        myMeasure = myPce.getLastMeasureOk(gazpar.TYPE_I)
                        if myMeasure:
                            logging.info("Last valid informative measure provided by GRDF : ")
                            logging.info("Date = %s", myMeasure.gasDate)
                            logging.info("Start index = %s, End index = %s", myMeasure.startIndex, myMeasure.endIndex)
                            logging.info("Volume = %s m3, Energy = %s kWh, Factor = %s", myMeasure.volume, myMeasure.energy,
                                         myMeasure.conversionFactor)
                            if myMeasure.isDeltaIndex:
                                logging.warning("Inconsistencies detected on the measure : ")
                                logging.warning(
                                    "Volume provided by Grdf (%s m3) has been replaced by the volume between start index and end index (%s m3)",
                                    myMeasure.volumeInitial, myMeasure.volume)
                        else:
                            logging.warning("Unable to find the last informative measure.")


                    # Get published measures
                    logging.info("---------------")
                    logging.info("Retrieve published measures...")
                    try:
                        myGrdf.getPceMeasures(myPce, startDate, endDate, gazpar.TYPE_P)
                        logging.info("Published measures found !")
                    except:
                        logging.error("Error during published measures collection")

                    # Analyse data
                    measureCount = myPce.countMeasure(gazpar.TYPE_P)
                    if measureCount > 0:
                        logging.info("Analysis of published measures provided by GRDF...")
                        logging.info("%s published measures provided by Grdf", measureCount)
                        measureOkCount = myPce.countMeasureOk(gazpar.TYPE_P)
                        logging.info("%s published measures are ok", measureOkCount)
                        accuracy = round((measureOkCount / measureCount) * 100)
                        logging.info("Accuracy is %s percent", accuracy)

                        # Get last published measure
                        myMeasure = myPce.getLastMeasureOk(gazpar.TYPE_P)
                        if myMeasure:
                            logging.info("Last valid published measure provided by GRDF : ")
                            logging.info("Start date = %s, End date = %s", myMeasure.startDateTime, myMeasure.endDateTime)
                            logging.info("Start index = %s, End index = %s", myMeasure.startIndex, myMeasure.endIndex)
                            logging.info("Volume = %s m3, Energy = %s kWh, Factor = %s", myMeasure.volume, myMeasure.energy,
                                         myMeasure.conversionFactor)
                            if myMeasure.isDeltaIndex:
                                logging.warning("Inconsistencies detected on the measure : ")
                                logging.warning(
                                    "Volume provided by Grdf (%s m3) has been replaced by the volume between start index and end index (%s m3)",
                                    myMeasure.volumeInitial, myMeasure.volume)
                        else:
                            logging.warning("Unable to find the last published measure.")

                    # Store to database
                    logging.info("---------------")
                    if myPce.measureList:
                        logging.info("Update of database with retrieved measures...")
                        for myMeasure in myPce.measureList:
                            # Store measure into database
                            myMeasure.store(myDb)

                        # Commmit database
                        myDb.commit()
                        logging.info("Database updated !")

                    else:
                        logging.info("Unable to store any measure for PCE %s to database !",myPce.pceId)


                    # Sub-step 3D : Get thresolds of the PCE

                    # Get thresold
                    logging.info("---------------")
                    logging.info("Retrieve PCE's thresolds from GRDF...")
                    try:
                        myGrdf.getPceThresold(myPce)
                        thresoldCount = myPce.countThresold()
                        logging.info("%s thresolds found !",thresoldCount)

                    except:
                        logging.error("Error to get PCE's thresolds from GRDF")

                    # Update database
                    if myPce.thresoldList:
                        # Store thresolds into database
                        logging.info("Update of database with retrieved thresolds...")
                        for myThresold in myPce.thresoldList:
                            myThresold.store(myDb)
                        # Commmit database
                        myDb.commit()
                        logging.info("Database updated !")


                    # Sub-step 3E : Calculate measures of the PCE

                    # Calculate informative measures
                    try:
                        myPce.calculateMeasures(myDb,myParams.thresoldPercentage,gazpar.TYPE_I)
                    except:
                        logging.error("Unable to calculate informative measures")


            else:
                logging.info("No PCE retrieved.")


           
    ####################################################################################################################
    # STEP 5C : Home Assistant period sensor load from dB
    ####################################################################################################################
    if myMqtt.isConnected \
        and myParams.hassDiscovery :

        try:

            logging.info("-----------------------------------------------------------")
            logging.info("#           Home assistant period sensor                  #")
            logging.info("-----------------------------------------------------------")

            # Create hass instance
            #myHass = hass.Hass(myParams.hassPrefix)
            
            #load data from dB
            myDb.load()
            # Loop on PCEs
            for myPce in myDb.pceList:

                logging.info("Publishing period values of PCE %s alias %s...",myPce.pceId,myPce.alias)
                logging.info("---------------------------------")

                # Create entity PCE
                if myParams.hassPeriodSensor and int(myParams.hassPeriodSensorCount) > 0:
                    logging.debug("Hass period sensor requested: %s, with max number of measures: %s ", myParams.hassPeriodSensor, myParams.hassPeriodSensorCount)
                    logging.info("Creation of the PCE_PERIOD measured entity")
                    myEntity = hass.Entity(myDevice,hass.SENSOR,'pce_period','pce_period',hass.NONE_TYPE,None,None)
                    myEntity.setValue(myPce.state)
                    myEntity.addAttribute("pce_alias",myPce.alias)
                    myEntity.addAttribute("pce_id",myPce.pceId)
                    myEntity.addAttribute("measure_frequency",myPce.frequenceReleve)
                    myEntity.addAttribute("activation_date",myPce.activationDate.strftime('%Y-%m-%d'))                    
                    myEntity.addAttribute("owner_name",myPce.ownerName)
                    myEntity.addAttribute("postal_code",myPce.postalCode)
                
                    # store last 10 values for use in HA directly
                    logging.info("Publishing values to HA Sensor PCE_PERIOD...")
                    logging.info("---------------------------------")
                    attributes = {}
                    if myPce.measureList:
                        logging.info("Update sensor with retrieved measures...")
                        attributes[f'period_enddate'] = []
                        attributes[f'period_energy'] = []
                        attributes[f'period_average'] = []
                        for myMeasure in myPce.measureList:
                            # Store measure into sensor
                            delta = datetime.datetime.strptime(myMeasure.periodEnd, '%Y-%m-%d') - datetime.datetime.strptime(myMeasure.periodStart, '%Y-%m-%d')
                            attributes[f'period_enddate'].append(str(myMeasure.periodEnd))
                            attributes[f'period_energy'].append(myMeasure.energy)
                            attributes[f'period_average'].append(int(myMeasure.energy / delta.days))
                            logging.debug("Updated sensor with period enddate: %s", myMeasure.periodEnd)
                            logging.debug("Updated sensor with period energy: %s", myMeasure.energy)
                            logging.debug("Updated sensor with period average (integer): %s", int(myMeasure.energy / delta.days))
                            
                            # limit number of measures, i.e. if (daily) gazpar is active, then this may explode on amount of data
                            if myPce.measureList.index(myMeasure) <= int(myParams.hassPeriodSensorCount):
                                logging.debug("next manual measure")
                        
                        myEntity.addAttribute("periodreg",attributes[f'period_enddate'])
                        myEntity.addAttribute("periodcon",attributes[f'period_energy'])
                        myEntity.addAttribute("periodavg",attributes[f'period_average'])
                                  
                    logging.info("Measures added to PCE_PERIOD sensor !")                                                       

                # Publish config, state (when value not none), attributes (when not none)
                logging.info("Publishing period devices...")
                logging.info("You can retrieve published values subscribing topic %s",myDevice.hass.prefix + "/+/" + myDevice.id + "/#")
                for topic,payload in myDevice.getStatePayload().items():
                    myMqtt.publish(topic,payload)
                logging.info("Devices published !")

        except:
            logging.error("Home Assistant discovery mode : unable to publish period value to mqtt broker")
            logging.error(traceback.format_exc())
    
    
    
    

    ####################################################################################################################
    # STEP 6 : Disconnect mqtt broker
    ####################################################################################################################
    if myMqtt.isConnected:

        logging.info("-----------------------------------------------------------")
        logging.info("#               Disconnexion from MQTT                    #")
        logging.info("-----------------------------------------------------------")

        try:
            myMqtt.disconnect()
            logging.info("Mqtt broker disconnected")
        except:
            logging.error("Unable to disconnect mqtt broker")
            sys.exit(1)

    # Release memory
    del myMqtt
    del myGrdf


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
