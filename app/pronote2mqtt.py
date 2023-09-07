#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pycron
import sys
import datetime
import schedule
import time
from dateutil.relativedelta import relativedelta
import logging
import collections
import re

import mqtt
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

# added to normalise topic in case of other characters such as accent, umlaut, etc.
import unidecode


# pronote2mqtt constants
P2M_VERSION = '0.6.x'
P2M_DB_VERSION = '0.2.0'

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

            # Display some (!) current database statistics
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
    myPronote = pronote.Pronote()

#Kick off for Student 1
    logging.info("Student 1-----------------------------------------------------")
    try:
        myPronote.getData(myParams.pronotePrefixUrl_1,myParams.pronoteUsername_1,myParams.pronotePassword_1,myParams.pronoteCas_1,myParams.pronoteGradesAverages_1,myParams.pronoteParent_1,myParams.pronoteFullName_1)
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
            
        for myPunishment in myPronote.punishmentList:
            myPunishment.store(myDb)    
        
        myDb.commit()
    except: 
        logging.error("Unable to properly connect for Student 1")

#Kick off for Student 2
    if myParams.pronoteUsername_2:
        logging.info("Student 2-----------------------------------------------------")
        try:
            myPronote.getData(myParams.pronotePrefixUrl_2,myParams.pronoteUsername_2,myParams.pronotePassword_2,myParams.pronoteCas_2,myParams.pronoteGradesAverages_2,myParams.pronoteParent_2,myParams.pronoteFullName_2)
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

            for myPunishment in myPronote.punishmentList:
                myPunishment.store(myDb)              
            
            myDb.commit()
        except: 
            logging.error("Unable to properly connect for Student 2")
   
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
    # STEP 3 : Home Assistant sensors load/create from dB
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
                deviceId = myParams.hassDeviceName.replace(" ","_") + "_" +  unidecode.unidecode(myStudent.studentFullname.replace(" ","_"))
                deviceName = myParams.hassDeviceName + " " +  unidecode.unidecode(myStudent.studentFullname)
                myDevice = hass.Device(myHass,myStudent.sid,deviceId,deviceName)
                
                # Create entity Student
                logging.info("Creation of the Student entity")
                myEntity = hass.Entity(myDevice,hass.SENSOR,'student','student',hass.NONE_TYPE,None,None)
                myEntity.setValue(unidecode.unidecode(myStudent.studentFullname))
                myEntity.addAttribute("school",myStudent.studentSchool)
                myEntity.addAttribute("current_class",myStudent.studentClass)
                
                # create homework sensor
                logging.info("Creation of the HOMEWORK entity")
                myEntity = hass.Entity(myDevice,hass.SENSOR,'homework','homework',hass.NONE_TYPE,None,None)
                myEntity.setValue(unidecode.unidecode(myStudent.studentFullname))                 
                
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
                        attributes[f'date'].append(myHomework.homeworkDate)
                        attributes[f'title'].append(myHomework.homeworkSubject)
                        attributes[f'description'].append(re.sub(r'http\S+', '<URL REMOVED, see PRONOTE-APP>', myHomework.homeworkDescription))
                        attributes[f'done'].append(myHomework.homeworkDone)                       
                       
                    myEntity.addAttribute("date",attributes[f'date'])
                    myEntity.addAttribute("title",attributes[f'title'])
                    myEntity.addAttribute("description",attributes[f'description'])
                    myEntity.addAttribute("done",attributes[f'done'])
                                  
                    logging.info("Homework added to HA sensor !")

                # create evaluation sensor
                logging.info("Creation of the EVALUATION/Acquisitions entity")
                myEntity = hass.Entity(myDevice,hass.SENSOR,'evaluation','evaluation',hass.NONE_TYPE,None,None)
                myEntity.setValue(unidecode.unidecode(myStudent.studentFullname))
                logging.info("Collecting and Publishing values Evaluation from shortlist (last x days)...")
                attributes = {}
                if myStudent.evaluationShortList:
                    logging.info("Collecting and Publishing values Evaluation from shortlist (last x days)...")
                    logging.info("---------------------------------")
                    attributes[f'date'] = []
                    attributes[f'subject'] = []
                    attributes[f'acquisition_name'] = []
                    attributes[f'acquisition_level'] = []
                    for myEvaluation in myStudent.evaluationShortList:
                        # Store evaluation into sensor
                        attributes[f'date'].append(myEvaluation.evalDate)
                        attributes[f'subject'].append(myEvaluation.evalSubject)
                        attributes[f'acquisition_name'].append(myEvaluation.acqName)
                        attributes[f'acquisition_level'].append(myEvaluation.acqLevel)
                        
                       
                    myEntity.addAttribute("date",attributes[f'date'])
                    myEntity.addAttribute("subject",attributes[f'subject'])
                    myEntity.addAttribute("acquisition_name",attributes[f'acquisition_name'])
                    myEntity.addAttribute("acquisition_level",attributes[f'acquisition_level'])
                                  
                    logging.info("Evaluation added to HA sensor !")
                
                # create absences sensor
                logging.info("Creation of the Absences entity")
                myEntity = hass.Entity(myDevice,hass.SENSOR,'absence','absence',hass.NONE_TYPE,None,None)
                myEntity.setValue(unidecode.unidecode(myStudent.studentFullname))
                logging.info("Collecting and Publishing values Absences from shortlist (last x days)...")
                attributes = {}
                if myStudent.absenceShortList:
                    logging.info("Collecting and Publishing values Absence from shortlist (last x days)...")
                    logging.info("---------------------------------")
                    attributes[f'from_date'] = []
                    attributes[f'hours'] = []
                    attributes[f'justified'] = []
                    attributes[f'reasons'] = []
                    for myAbsence in myStudent.absenceShortList:
                        # Store evaluation into sensor
                        attributes[f'from_date'].append(myAbsence.absenceFrom.split("/",1)[1])
                        attributes[f'hours'].append(myAbsence.absenceHours)
                        attributes[f'justified'].append(myAbsence.absenceJustified)
                        attributes[f'reasons'].append(myAbsence.absenceReasons)
                        
                       
                    myEntity.addAttribute("date",attributes[f'from_date'])
                    myEntity.addAttribute("hours",attributes[f'hours'])
                    myEntity.addAttribute("justified",attributes[f'justified'])
                    myEntity.addAttribute("reason",attributes[f'reasons'])
                                  
                    logging.info("Absence added to HA sensor !")  

                # create averages sensor
                logging.info("Creation of the Averages entity")
                myEntity = hass.Entity(myDevice,hass.SENSOR,'average','average',hass.NONE_TYPE,None,None)
                myEntity.setValue(unidecode.unidecode(myStudent.studentFullname))
                logging.info("Collecting and Publishing values Averages for last period...")
                attributes = {}
                if myStudent.averageList:
                    logging.info("Collecting and Publishing values Average for last period...")
                    logging.info("---------------------------------")
                    attributes[f'subject'] = []
                    attributes[f'student_average'] = []
                    attributes[f'class_average'] = []
                    attributes[f'max'] = []
                    attributes[f'min'] = []
                    for myAverage in myStudent.averageList:
                        # Store evaluation into sensor
                        attributes[f'subject'].append(myAverage.subject)
                        attributes[f'student_average'].append(myAverage.studentAverage)
                        attributes[f'class_average'].append(myAverage.classAverage)
                        attributes[f'max'].append(myAverage.max)
                        attributes[f'min'].append(myAverage.min)
                        
                    myEntity.addAttribute("subject",attributes[f'subject'])   
                    myEntity.addAttribute("student_average",attributes[f'student_average'])
                    myEntity.addAttribute("class_average",attributes[f'class_average'])
                    myEntity.addAttribute("max",attributes[f'max'])
                    myEntity.addAttribute("min",attributes[f'min'])
                                  
                    logging.info("Average added to HA sensor !")                         
                
                # create grades sensor
                logging.info("Creation of the Grades entity")
                myEntity = hass.Entity(myDevice,hass.SENSOR,'grade','grade',hass.NONE_TYPE,None,None)
                myEntity.setValue(unidecode.unidecode(myStudent.studentFullname))
                logging.info("Collecting and Publishing values Grades from shortlist (last x days)...")
                attributes = {}
                if myStudent.gradeList:
                    logging.info("Collecting and Publishing values Grades from shortlist (last x days)...")
                    logging.info("---------------------------------")
                    attributes[f'date'] = []
                    attributes[f'subject'] = []
                    attributes[f'student_grade'] = []
                    attributes[f'grade'] = []
                    attributes[f'out_of'] = []
                    attributes[f'class_average'] = []
                    attributes[f'coefficient'] = []
                    attributes[f'max'] = []
                    attributes[f'min'] = []
                    attributes[f'comment'] = []
                    for myGrade in myStudent.gradeList:
                        # Store evaluation into sensor
                        attributes[f'date'].append(myGrade.date)
                        attributes[f'subject'].append(myGrade.subject)
                        attributes[f'student_grade'].append(myGrade.defaultOutOf)
                        attributes[f'grade'].append(myGrade.grade)
                        attributes[f'out_of'].append(myGrade.outOf)
                        attributes[f'class_average'].append(myGrade.average)
                        attributes[f'coefficient'].append(myGrade.coefficient)
                        attributes[f'max'].append(myGrade.max)
                        attributes[f'min'].append(myGrade.min)
                        attributes[f'comment'].append(myGrade.comment)
                    
                    myEntity.addAttribute("date",attributes[f'date'])                    
                    myEntity.addAttribute("subject",attributes[f'subject'])   
                    myEntity.addAttribute("student_grade",attributes[f'student_grade'])
                    myEntity.addAttribute("grade",attributes[f'grade'])
                    myEntity.addAttribute("out_of",attributes[f'out_of'])
                    myEntity.addAttribute("class_average",attributes[f'class_average'])
                    myEntity.addAttribute("coefficient",attributes[f'coefficient'])
                    myEntity.addAttribute("max",attributes[f'max'])
                    myEntity.addAttribute("min",attributes[f'min'])
                    myEntity.addAttribute("comment",attributes[f'comment'])
                                  
                    logging.info("Grade added to HA sensor !")

                # create lessons sensor
                logging.info("Creation of the Lesson entity")
                myEntity = hass.Entity(myDevice,hass.SENSOR,'lesson','lesson',hass.NONE_TYPE,None,None)
                myEntity.setValue(unidecode.unidecode(myStudent.studentFullname))
                attributes = {}
                if myStudent.lessonShortList:
                    logging.info("Collecting and Publishing values Lessons from shortlist (last x days)...")
                    logging.info("---------------------------------")
                    attributes[f'date'] = []
                    attributes[f'start'] = []
                    attributes[f'end'] = []
                    attributes[f'subject'] = []
                    attributes[f'canceled'] = []
                    attributes[f'status'] = []
                    attributes[f'room'] = []
                    for index, myLesson in enumerate(myStudent.lessonShortList):
                        # Store lesson into sensor 
                        # Fix: filter out 'duplicates', i.e. canceled lessons in case other registration for same slot
                        # Fix: note that this assumes the data to be provided 'sorted' by datetime ASC and lessonnum DESC(see database.by) 
                        if not (myStudent.lessonShortList[index].lessonDateTime == myStudent.lessonShortList[index-1].lessonDateTime):
                        # and myStudent.lessonShortList[index].lessonNum > myStudent.lessonShortList[index-1].lessonNum):
                                attributes[f'date'].append(myLesson.lessonDateTime.split(" ",1)[0])
                                attributes[f'start'].append(myLesson.lessonStart)
                                attributes[f'end'].append(myLesson.lessonEnd)
                                attributes[f'subject'].append(myLesson.lessonSubject)
                                attributes[f'canceled'].append(myLesson.lessonCanceled)
                                attributes[f'status'].append(myLesson.lessonStatus)
                                attributes[f'room'].append(myLesson.lessonRoom)
                    
                    myEntity.addAttribute("date",attributes[f'date'])                    
                    myEntity.addAttribute("start",attributes[f'start'])   
                    myEntity.addAttribute("end",attributes[f'end'])
                    myEntity.addAttribute("subject",attributes[f'subject'])
                    myEntity.addAttribute("canceled",attributes[f'canceled'])
                    myEntity.addAttribute("status",attributes[f'status'])
                    myEntity.addAttribute("room",attributes[f'room'])
                                  
                    logging.info("Lesson added to HA sensor !")                      
                              
                # create punishment sensor
                logging.info("Creation of the Punishment entity")
                myEntity = hass.Entity(myDevice,hass.SENSOR,'punishment','punishment',hass.NONE_TYPE,None,None)
                myEntity.setValue(unidecode.unidecode(myStudent.studentFullname))
                logging.info("Collecting and Publishing values Punishments from shortlist/period...")
                attributes = {}
                if myStudent.punishmentShortList:
                    logging.info("Collecting and Publishing values Punishment from shortlist/period...")
                    logging.info("---------------------------------")
                    attributes[f'pundate'] = []
                    attributes[f'reasons'] = []
                    attributes[f'circumstances'] = []
                    attributes[f'nature'] = []
                    attributes[f'duration'] = []
                    attributes[f'homework'] = []
                    attributes[f'exclusion'] = []
                    
                    for myPunishment in myStudent.punishmentShortList:
                        # Store evaluation into sensor
                        attributes[f'pundate'].append(myPunishment.punishmentDate.split("/",1)[1])
                        attributes[f'reasons'].append(myPunishment.punishmentReasons)
                        attributes[f'circumstances'].append(myPunishment.punishmentCircumstances)
                        attributes[f'nature'].append(myPunishment.punishmentNature)
                        attributes[f'duration'].append((myPunishment.punishmentDuration)[:4])
                        attributes[f'homework'].append(myPunishment.punishmentHomework)
                        attributes[f'exclusion'].append(myPunishment.punishmentExclusion)
                        
                       
                    myEntity.addAttribute("date",attributes[f'pundate'])
                    myEntity.addAttribute("reasons",attributes[f'reasons'])
                    myEntity.addAttribute("circumstances",attributes[f'circumstances'])
                    myEntity.addAttribute("nature",attributes[f'nature'])
                    myEntity.addAttribute("duration",attributes[f'duration'])
                    myEntity.addAttribute("homework",attributes[f'homework'])
                    myEntity.addAttribute("exclusion",attributes[f'exclusion'])
                                  
                    logging.info("Punishment added to HA sensor !")  
                    
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
    # STEP 4 : Disconnect mqtt broker (throws errors....to fix in future)
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
    logging.info("Cleaning up previous run")
    del myPronote
    del myMqtt

    ####################################################################################################################
    # STEP 5 : Disconnect from database
    ####################################################################################################################
    logging.info("-----------------------------------------------------------")
    logging.info("#          Disconnexion from SQLite database              #")
    logging.info("-----------------------------------------------------------")

    if myDb.isConnected() :
        myDb.close()
        logging.info("SQLite database disconnected")
    del myDb

    ####################################################################################################################
    # STEP 6 : Display next run info and end of program
    ####################################################################################################################
    logging.info("-----------------------------------------------------------")
    logging.info("#                Next run                                 #")
    logging.info("-----------------------------------------------------------")
    if myParams.scheduleCron:
        logging.info("The pronote2mqtt runs are cron scheduled => %s (hour / range / daymth / mth / weekdays )",myParams.scheduleCron)  
    else:
        logging.info("No schedule or frequency  defined.")

   
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
    
    # Run once at lauch
    run(myParams)
    
    def job():
        timenow = time.localtime()
        logging.info("-----------------------------------------------------------")
        logging.info("Pronotepy-cron-job at:... %s", str( time.strftime("%H:%M", timenow) )) 
        logging.info("-----------------------------------------------------------")
        run(myParams)
    

    if myParams.scheduleCron is not None:
        
        logging.info("-----------------------------------------------------------")
        logging.info("Awaiting cron to kick off => %s (hour / range / daymth / mth / weekdays", myParams.scheduleCron)  
        logging.info("-----------------------------------------------------------")
        
        while True:    
            if pycron.is_now(myParams.scheduleCron):
                logging.info("-----------------------------------------------------------")
                logging.info("In scheduler (pycron)")  
                logging.info("-----------------------------------------------------------")
                job()
            time.sleep(60)
            
    else:      
        # Run once
        logging.info("-----------------------------------------------------------")
        logging.info("Only run once, no schedule")
        logging.info("-----------------------------------------------------------")
        run(myParams)
        logging.info("End of pronote2mqtt.")


