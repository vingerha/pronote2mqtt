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
#import standalone
import hass
import param
import database
import traceback

#imports for pronotepy
import pronotepy
import os
from datetime import date
from datetime import timedelta
import json

import pronote


# gazpar2mqtt constants
P2M_VERSION = '0.1.0'
P2M_DB_VERSION = '0.1.0'

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
    myDb.connect(P2M_VERSION,P2M_DB_VERSION)
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
        myDb.reInit(P2M_VERSION,P2M_DB_VERSION)
        logging.info("Database reinitialized to version %s",P2M_DB_VERSION)
    else:
        # Compare dabase version
        logging.info("Checking database version...")
        dbVersion = myDb.getConfig(database.DB_KEY)
        if dbVersion == P2M_DB_VERSION:
            logging.info("Your database is already up to date : version %s.",P2M_DB_VERSION)

            # Display current database statistics
            logging.info("Retrieve database statistics...")
            dbStats = myDb.getGradesCount()
            logging.info("%s informatives grades stored", dbStats["rows"])
            logging.info("%s Grade(s)", dbStats["gid"])
            logging.info("First grade : %s", dbStats["minDate"])
            logging.info("Last grade : %s", dbStats["maxDate"])

        else:
            logging.warning("Your database (version %s) is not up to date.",dbVersion)
            logging.info("Reinitialization of your database to version %s...",P2M_DB_VERSION)
            myDb.reInit(P2M_VERSION,P2M_DB_VERSION)
            dbVersion = myDb.getConfig(database.DB_KEY)
            logging.info("Database reinitialized to version %s !",dbVersion)

    ####################################################################################################################
    # STEP 1 : Collect data from pronote
    ####################################################################################################################
    logging.info("-----------------------------------------------------------")
    logging.info("#          Collection from Pronote                         #")
    logging.info("-----------------------------------------------------------")
    logging.info("Grades-----------------------------------------------------")
    myPronote = pronote.Pronote()
    
#Kick off for Student 1
    myPronote.getData(myParams.pronotePrefixUrl_1,myParams.pronoteUsername_1,myParams.pronotePassword_1,myParams.pronoteStudent_1,myParams.pronoteCas_1,myParams.pronoteGradesAverages_1)
    if myParams.pronoteGradesAverages_1:
        for myAverage in myPronote.averageList:
            myAverage.store(myDb)
        for myGrade in myPronote.gradeList:
            myGrade.store(myDb)
 
    for myPeriod in myPronote.periodList:
        myPeriod.store(myDb)
    
    if not myParams.pronoteGradesAverages_1:    
        for myEval in myPronote.evalList:
            myEval.store(myDb)

    for myLesson in myPronote.lessonList:
        myLesson.store(myDb)

    for myHomework in myPronote.homeworkList:
        myHomework.store(myDb)

    for myStudent in myPronote.studentList:
        myStudent.store(myDb)
        
    for myAbsence in myPronote.absenceList:
        myAbsence.store(myDb)
    
    myDb.commit()

#Kick off for Student 2
    myPronote.getData(myParams.pronotePrefixUrl_2,myParams.pronoteUsername_2,myParams.pronotePassword_2,myParams.pronoteStudent_2,myParams.pronoteCas_2,myParams.pronoteGradesAverages_2)
    if myParams.pronoteGradesAverages_2:
        for myAverage in myPronote.averageList:
            myAverage.store(myDb)
        for myGrade in myPronote.gradeList:
            myGrade.store(myDb)
 
    for myPeriod in myPronote.periodList:
        myPeriod.store(myDb)
    
    if not myParams.pronoteGradesAverages_2:    
        for myEval in myPronote.evalList:
            myEval.store(myDb)

    for myLesson in myPronote.lessonList:
        myLesson.store(myDb)

    for myHomework in myPronote.homeworkList:
        myHomework.store(myDb)
        
    for myStudent in myPronote.studentList:
        myStudent.store(myDb)
        
    for myAbsence in myPronote.absenceList:
        myAbsence.store(myDb)        
    
    myDb.commit()
    
    
    ####################################################################################################################
    # STEP 2 : Connect to MQTT
    ####################################################################################################################
    ####################################################################################################################
    logging.info("-----------------------------------------------------------")
    logging.info("#              Connexion to Mqtt broker                   #")
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

    ####################################################################################################################
    # STEP 5C : Home Assistant period sensor load from dB
    ####################################################################################################################
    if myMqtt.isConnected \
        and myParams.hassDiscovery :

        try:

            logging.info("-----------------------------------------------------------")
            logging.info("#           Home assistant sensor                         #")
            logging.info("-----------------------------------------------------------")

            # Create hass instance
            myHass = hass.Hass(myParams.hassPrefix)
            
            #load data from dB
            myDb.load()
            # Loop on students
            for myStudent in myDb.studentList:
                  
                logging.info("Publishing period values of Students %s alias %s...", myStudent.sid, myStudent.studentFullname)
                logging.info("---------------------------------")
                
                # Create the device corresponding to the user
                deviceId = myParams.hassDeviceName.replace(" ","_") + "_" +  myStudent.sid
                deviceName = myParams.hassDeviceName + " " +  myStudent.studentFullname
                myDevice = hass.Device(myHass,myStudent.sid,deviceId,deviceName)
                
                # Create entity Student
                logging.info("Creation of the Student entity")
                myEntity = hass.Entity(myDevice,hass.SENSOR,'student','student',hass.NONE_TYPE,None,None)
                myEntity.setValue(myStudent.studentFullname)
                myEntity.addAttribute("school",myStudent.studentSchool)
                myEntity.addAttribute("current_class",myStudent.studentClass)
                
                # create homework sensor
                logging.info("Creation of the HOMEWORK entity")
                myEntity = hass.Entity(myDevice,hass.SENSOR,'homework','homework',hass.NONE_TYPE,None,None)
                myEntity.setValue(myStudent.studentFullname)
                myEntity.addAttribute("current_class",myStudent.studentClass)
                myEntity.addAttribute("load_time",datetime.date.today().strftime("%Y/%m/%d"))                    
                
                attributes = {}
                if myStudent.homeworkList:
                    logging.info("Collecting and Publishing values Homework...")
                    logging.info("---------------------------------")
                    attributes[f'date'] = []
                    attributes[f'title'] = []
                    attributes[f'description'] = []
                    attributes[f'done'] = []
                    for myHomework in myStudent.homeworkList:
                        # Store homework into sensor
                        attributes[f'date'].append(myHomework.homeworkDate.split("/",1)[1])
                        attributes[f'title'].append(myHomework.homeworkSubject)
                        attributes[f'description'].append(myHomework.homeworkDescription)
                        attributes[f'done'].append(myHomework.homeworkDone)
                        
                       
                    myEntity.addAttribute("date",attributes[f'date'])
                    myEntity.addAttribute("title",attributes[f'title'])
                    myEntity.addAttribute("description",attributes[f'description'])
                    myEntity.addAttribute("done",attributes[f'done'])
                                  
                    logging.info("Homework added to HA sensor !")

                # create evaluation sensor
                logging.info("Creation of the EVALUATION/Acquisitions entity")
                myEntity = hass.Entity(myDevice,hass.SENSOR,'evaluation','evaluation',hass.NONE_TYPE,None,None)
                myEntity.setValue(myStudent.studentFullname)
                myEntity.addAttribute("current_class",myStudent.studentClass)
                myEntity.addAttribute("load_time",datetime.date.today().strftime("%Y/%m/%d"))                    
                
                attributes = {}
                if myStudent.evaluationShortList:
                    logging.info("Collecting and Publishing values Evaluation from shortlist (last x days)...")
                    logging.info("---------------------------------")
                    attributes[f'date'] = []
                    attributes[f'subject'] = []
                    attributes[f'acquisition_name'] = []
                    attributes[f'acquisition_level'] = []
                    for myEvaluation in myStudent.evaluationShortList:
                        # Store homework into sensor
                        attributes[f'date'].append(myEvaluation.evalDate.split("/",1)[1])
                        attributes[f'subject'].append(myEvaluation.evalSubject)
                        attributes[f'acquisition_name'].append(myEvaluation.acqName)
                        attributes[f'acquisition_level'].append(myEvaluation.acqLevel)
                        
                       
                    myEntity.addAttribute("date",attributes[f'date'])
                    myEntity.addAttribute("subject",attributes[f'subject'])
                    myEntity.addAttribute("acquisition_name",attributes[f'acquisition_name'])
                    myEntity.addAttribute("acquisition_level",attributes[f'acquisition_level'])
                                  
                    logging.info("Evaluation added to HA sensor !")                    
                
  
                
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
        logging.info("The pronote2mqtt next run is scheduled at %s",myParams.scheduleTime)
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
    logging.info("#               Welcome to pronote2mqtt                    #")
    logging.info("-----------------------------------------------------------")
    logging.info("Program version : %s",P2M_VERSION)
    logging.info("Database version : %s", P2M_DB_VERSION)
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
        logging.info("End of pronote2mqtt.")
