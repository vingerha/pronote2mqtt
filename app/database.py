#!/usr/bin/env python3
import sqlite3
import os
import logging
import datetime
import json
from dateutil.relativedelta import *

# Constants
DATABASE_NAME = "pronote2mqtt.db"
DATABASE_TIMEOUT = 10
DATABASE_DATE_FORMAT = "%Y-%m-%d"
DATABASE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Config constants
P2M_KEY = "p2m"
DB_KEY = "db"
LAST_EXEC_KEY = "last_exec_datetime"

# Convert datetime string to datetime
def _convertDate(dateString):
    if dateString == None: return None
    else:
        myDateTime = datetime.datetime.strptime(dateString,DATABASE_DATE_FORMAT)
        return myDateTime

def _convertDateTime(dateString):
  if dateString == None:
    return None
  else:
    myDateTime = datetime.datetime.strptime(dateString, DATABASE_DATETIME_FORMAT)
    return myDateTime

# Class database
class Database:
  
  # Constructor
  def __init__(self,path):
  
    self.con = None
    self.cur = None
    self.date = datetime.datetime.now().strftime('%Y-%m-%d')
    self.p2mVersion = None
    self.dbVersion = None
    self.path = path
    self.studentList = []
  
  # Database initialization
  def init(self,p2mVersion,dbVersion):

    # Create table for configuration
    logging.debug("Creation of config table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS config (
                                key TEXT NOT NULL
                                , value TEXT NOT NULL)''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_config_key
                            ON config (key)''')
                            
    ## Create table of  Students
    logging.debug("Creation of Students table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS students (
                        sid TEXT
                        , fullname TEXT
                        , school TEXT
                        , class TEXT
                        , PRIMARY KEY (fullname))''')
    ## Create table of  Periods
    logging.debug("Creation of Period table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS periods (
                        pid TEXT
                        , studentname TEXT
                        , name TEXT
                        , start TEXT
                        , end TEXT
                        , PRIMARY KEY (studentname,name,start))''')
    ## Create table of grades
    logging.debug("Creation of Grade table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS grades (
                        pid TEXT NOT NULL
                        , period_name TEXT
                        , period_start TEXT
                        , period_end TEXT
                        , gid TEXT
                        , studentname TEXT
                        , date TEXT
                        , subject TYPE TEXT
                        , grade TYPE TEXT
                        , out_of TYPE TEXT
                        , default_out_of TYPE TEXT
                        , coefficient TYPE TEXT
                        , average TYPE TEXT
                        , max TEXT
                        , min TEXT
                        , comment TYPE TEXT
                        , PRIMARY KEY (period_name,date,subject,comment))''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_grades_date
                    ON grades (period_name,date,subject,comment)''')

    ## Create table of averages
    ## pronote does not supply an id used period-id
    logging.debug("Creation of Averages table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS averages (
                        pid TEXT NOT NULL
                        , period_name TEXT
                        , period_start TEXT
                        , period_end TEXT
                        , studentname TEXT NOT NULL
                        , student TEXT
                        , class_average TEXT
                        , max TYPE TEXT
                        , min TYPE TEXT
                        , out_of TYPE TEXT
                        , default_out_of TYPE TEXT
                        , subject TYPE TEXT NOT NULL
			, PRIMARY KEY(period_name,studentname,subject))''')

    # using key on period id and evalid
    logging.debug("Creation of Evaluations table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS evaluations (
                        pid TEXT NOT NULL
                        , period_name TEXT
                        , period_start TEXT
                        , period_end TEXT
                        , studentname TEXT
                        , eid TEXT NOT NULL
                        , name TEXT
                        , domain TEXT
                        , teacher TEXT
                        , coefficient TEXT
                        , description TEXT
                        , subject TEXT
                        , date TEXT
                        , aid TEXT
                        , acquisition_name TEXT NOT NULL DEFAULT "na"
                        , acquisition_abbreviation TEXT
                        , acquisition_level TEXT
                        , acquisition_domain TEXT
                        , acquisition_coefficient TEXT
                        , PRIMARY KEY(period_name,studentname,subject,date,aid,acquisition_name,acquisition_level, acquisition_domain,acquisition_coefficient))''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_evaluations_aid
                    ON evaluations (period_name,studentname,subject,date,aid,acquisition_name,acquisition_level,acquisition_domain,acquisition_coefficient)''')
                      
    # using key on period id and evalid
    logging.debug("Creation of Absences table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS absences (
                        pid TEXT NOT NULL
                        , period_name TEXT
                        , period_start TEXT
                        , period_end TEXT
                        , studentname TEXT
                        , abid TEXT NOT NULL
                        , from_date TEXT
                        , to_date TEXT
                        , justified TEXT
                        , hours TEXT
                        , days TEXT
                        , reasons TEXT
                        , PRIMARY KEY(period_name,studentname,from_date,reasons))''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_absences_pidabid
                    ON absences (period_name,studentname,from_date,reasons)''')   
   
    # using key on period id and evalid
    logging.debug("Creation of Lessons table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS lessons (
                        lid TEXT NOT NULL
                        , studentname TEXT NOT NULL
                        , lessonDateTime TEXT
                        , lessonStart TEXT
                        , lessonEnd TEXT
                        , lessonSubject TEXT
                        , lessonRoom TEXT DEFAULT "nc" NOT NULL
                        , lessonCanceled TEXT
                        , lessonStatus TEXT DEFAULT "nc" NOT NULL
                        , lessonNum TEXT
                        , PRIMARY KEY(studentname,lessonDateTime,lessonSubject,lessonRoom, lessonCanceled, lessonCanceled))''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_lessons_lid
                    ON lessons (studentname,lessonDateTime,LessonSubject, lessonRoom, lessonStatus, lessonCanceled)''')

    # using key on period id and evalid
    logging.debug("Creation of Homework table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS homework (
                        hid TEXT NOT NULL
                        , studentname TEXT NOT NULL
                        , homeworkSubject TEXT
                        , homeworkDescription TEXT
                        , homeworkDone TEXT
                        , homeworkDate TEXT
                        , PRIMARY KEY(studentname,homeworkDate,homeworkSubject,homeworkDescription))''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_homework_hid
                    ON homework (studentname,homeworkDate,homeworkSubject,homeworkDescription)''')

    # using key on period id and evalid
    logging.debug("Creation of Punishments table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS punishments (
                        pid TEXT
                        , period_name TEXT
                        , period_start TEXT
                        , period_end TEXT
                        , studentname TEXT
                        , punid TEXT
                        , pundate TEXT
                        , during_lesson TEXT
                        , reasons TEXT
                        , circumstances TEXT
                        , nature TEXT
                        , duration
                        , homework TEXT
                        , exclusion TEXT
                        , PRIMARY KEY(studentname,pid,punid))''')
    # Commit
    self.commit()

    # Update configuration values
    logging.debug("Store configuration")
    self.updateVersion(P2M_KEY, p2mVersion)
    self.updateVersion(DB_KEY, dbVersion)
    self.updateVersion(LAST_EXEC_KEY, datetime.datetime.now())


    # Commit
    self.commit()

  # Check that table exists
  def existsTable(self,name):

    query = "SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?"
    queryResult = None
    try:
      self.cur.execute(query,[name])
      queryResult = self.cur.fetchall()
      if queryResult is not None and queryResult[0][0] == 1:
        return True
      else:
        return False
    except Exception as e:
      logging.error("Error when checking table : %s",e)
      return False


  # Update version
  def updateVersion(self,key,value):

    if self.existsTable("config"):
      query = "INSERT OR REPLACE INTO config(key,value) VALUES(?,?)"
      try:
        self.cur.execute(query, [key,value])
        logging.debug("Version of key %s with value %s updated successfully !", key, value)
      except Exception as e:
        logging.error("Error when updating config table : %s",e)


  # Get version
  def getConfig(self, key):

    query = "SELECT value FROM config WHERE key = ?"
    queryResult = None
    try:
      self.cur.execute(query,[key])
      queryResult = self.cur.fetchone()
      if queryResult is not None:
        return queryResult[0]
      else:
        return None
    except Exception as e:
      logging.warning("Error retrieving version of key %s in config table %s", key, e)
      return queryResult


  # Connexion to database
  def connect(self,g2mVersion,dbVersion):
    
    # Create directory if not exists
    if not os.path.exists(self.path):
        os.mkdir(self.path)
        logging.debug("Directory %s created",self.path)
    
    # Initialize database if not exists
    if not os.path.exists(self.path + "/" + DATABASE_NAME):
        logging.debug("Initialization of the SQLite database...")
        self.con = sqlite3.connect(self.path + "/" + DATABASE_NAME, timeout=DATABASE_TIMEOUT)
        self.cur = self.con.cursor()
        self.init(g2mVersion,dbVersion)
    else:
        logging.debug("Connexion to database")
        self.con = sqlite3.connect(self.path + "/" + DATABASE_NAME, timeout=DATABASE_TIMEOUT)
        self.cur = self.con.cursor()
        
# delete data from lessons as impossible to distinguish between historical records for a lesson and new/changed records for the very same lesson
# With the presented attribues, one cannot identify which has the real value/truth
    logging.debug("Delete today & future Lessons to fix mismatches/duplicates that avoid presenting the correct lesson/status")
    self.cur.execute('''DELETE from lessons where lessonDateTime >= date('now')''')        
        
  # Get measures statistics
  def getGradesCount(self):

    valueResult = {}
    query = f"SELECT count(*), count(distinct period_start), count(distinct gid), min(period_start), max(period_start) FROM grades"
    #  to add to distinguish between students.....e.g. WHERE student = '{sid}'"
    self.cur.execute(query)
    queryResult = self.cur.fetchone()
    if queryResult is not None:
            if queryResult[0] is not None:
                valueResult["rows"] = int(queryResult[0])
                valueResult["dates"] = int(queryResult[1])
                valueResult["gid"] = int(queryResult[2])
                valueResult["minDate"] = queryResult[3]
                valueResult["maxDate"] = queryResult[4]
                return valueResult


  # Re-initialize the database
  def reInit(self,p2mVersion,dbVersion):
    
    logging.debug("Reinitialization of the database.")
    
    logging.debug("Drop configuration table")
    self.cur.execute('''DROP TABLE IF EXISTS config''')
    
    logging.debug("Drop Periods table")
    self.cur.execute('''DROP TABLE IF EXISTS periods''')

    logging.debug("Drop Grades table")
    self.cur.execute('''DROP TABLE IF EXISTS grades''')

    logging.debug("Drop Averages table")
    self.cur.execute('''DROP TABLE IF EXISTS averages''')

    logging.debug("Drop Evaluations table")
    self.cur.execute('''DROP TABLE IF EXISTS evaluations''')

    logging.debug("Drop Lessons table")
    self.cur.execute('''DROP TABLE IF EXISTS lessons''')

    logging.debug("Drop Homework table")
    self.cur.execute('''DROP TABLE IF EXISTS homework''')

    logging.debug("Drop Student table")
    self.cur.execute('''DROP TABLE IF EXISTS students''')

    logging.debug("Drop Absences table")
    self.cur.execute('''DROP TABLE IF EXISTS absences''')

    logging.debug("Drop Punishment table")
    self.cur.execute('''DROP TABLE IF EXISTS punishments''')
       
    # Commit work
    self.commit()
    
    # Initialize tables
    self.init(p2mVersion,dbVersion)
      
        
  # Check if connected
  def isConnected(self):
    return self.cur
    
    
  # Disconnect
  def close(self):
    logging.debug("Disconnexion of the database")
    self.con.close()
    
    
  # Commit work
  def commit(self):
    self.con.commit()

  # Load
  def load(self):

    # Load Students
    self._loadStudents()
    
    #load Homework
    for myStudent in self.studentList:
        self._loadHomework(myStudent)

    #load Evaluation
    for myStudent in self.studentList:
        self._loadEvaluationsShortList(myStudent)

    #load Absence
    for myStudent in self.studentList:
        self._loadAbsenceShortList(myStudent)

    #load Averages
    for myStudent in self.studentList:
        self._loadAverage(myStudent)
        
    #load Grade
    for myStudent in self.studentList:
        self._loadGradesShortList(myStudent)        

    #load Lessons
    for myStudent in self.studentList:
        self._loadLessonsShortList(myStudent)

    #load Punishments
    for myStudent in self.studentList:
        self._loadPunishmentShortList(myStudent)
     
  # Load students
  def _loadStudents(self):

    query = "SELECT * FROM students"
    self.cur.execute(query)
    queryResult = self.cur.fetchall()

    # Create object Student
    for result in queryResult:
      myStudent = Student(result)
      self.studentList.append(myStudent)
      
  # Load homework
  def _loadHomework(self,student):
    studentname=student.studentFullname
    datestart = datetime.date.today().strftime("%Y/%m/%d")
    dateend = datetime.date.today() + relativedelta(days=7)
    dateend = dateend.strftime("%Y/%m/%d")
    query = f"SELECT * FROM homework WHERE studentname = '{studentname}' and homeworkDate between '{datestart}' and '{dateend}' order by homeworkDate"
    self.cur.execute(query)
    queryResult = self.cur.fetchall()
    # Create object Homework
    for result in queryResult:
      myHomework = Homework(result)
      student.homeworkList.append(myHomework)

  def _loadEvaluationsShortList(self,student):
    studentname=student.studentFullname
    # not collecting all 
    datestart = datetime.date.today() - relativedelta(days=30)
    datestart = datestart.strftime("%Y/%m/%d")
    query = f"SELECT * FROM evaluations WHERE studentname like '{studentname}' and date >= '{datestart}' ORDER by date desc"
    self.cur.execute(query)
    queryResult = self.cur.fetchall()
    # Create object Eval
    for result in queryResult:
      myEvaluation = Evaluations(result)
      student.evaluationShortList.append(myEvaluation)

  def _loadAbsenceShortList(self,student):
    studentname=student.studentFullname
    # not collecting all 
    datestart = datetime.date.today() - relativedelta(days=30)
    datestart = datestart.strftime("%Y/%m/%d %H:%M")
    query = f"SELECT * FROM absences WHERE studentname like '{studentname}' and from_date >= '{datestart}' and period_name like 'Année continue'"
    self.cur.execute(query)
    queryResult = self.cur.fetchall()
    # Create object Absence
    for result in queryResult:
      myAbsence = Absences(result)
      student.absenceShortList.append(myAbsence)    

  # Load averages
  def _loadAverage(self,student):
    studentname=student.studentFullname
    # averages have been loaded for all periods but are the same for all periods, extracting only Yeardata
    query = f"SELECT * FROM averages WHERE studentname like '{studentname}' and period_start = (select max(period_start) from averages)"
    self.cur.execute(query)
    queryResult = self.cur.fetchall()
    # Create object Homework
    for result in queryResult:
      myAverage = Averages(result)
      student.averageList.append(myAverage)
      
  # Load grades
  def _loadGradesShortList(self,student):
    studentname=student.studentFullname
    datestart = datetime.date.today() - relativedelta(days=30)
    datestart = datestart.strftime("%Y/%m/%d")
    query = f"SELECT * FROM grades WHERE studentname like '{studentname}' and date >= '{datestart}' ORDER by date desc"
    self.cur.execute(query)
    queryResult = self.cur.fetchall()
    # Create object Homework
    for result in queryResult:
      myGrade = Grades(result)
      student.gradeList.append(myGrade)  
   # load lessons
  def _loadLessonsShortList(self,student):
    studentname=student.studentFullname
    # not collecting all 
    datestart = datetime.date.today().strftime("%Y/%m/%d %H:%M")
    dateend = datetime.date.today() + relativedelta(days=7)
    dateend = dateend.strftime("%Y/%m/%d %H:%M")
    query = f"SELECT * FROM lessons WHERE studentname like '{studentname}' and lessonDateTime between '{datestart}' and '{dateend}' ORDER by lessonDateTime asc, CAST(lessonNum as INTEGER) desc"
    self.cur.execute(query)
    queryResult = self.cur.fetchall()
    # Create object Eval
    for result in queryResult:
      myLesson = Lessons(result)
      student.lessonShortList.append(myLesson)   

   # load punishments
  def _loadPunishmentShortList(self,student):
    studentname=student.studentFullname
    # punishments have been loaded for all periods but are the same for all periods, extracting last period
    query = f"SELECT * FROM punishments WHERE studentname like '{studentname}' and period_name like 'Année continue' ORDER by pundate desc"
    self.cur.execute(query)
    queryResult = self.cur.fetchall()
    # Create object Punishment
    for result in queryResult:
      myPunishment = Punishments(result)
      student.punishmentShortList.append(myPunishment)       

# classes
class Grades():

  def __init__(self,result):

    self.pid = result[0]
    self.period_name = result[1]
    self.period_start = result[2]
    self.period_end = result[3]
    self.gid = result[4]
    self.student = result[5]
    self.date = result[6]
    self.subject = result[7]
    self.grade = result[8]
    self.outOf = result[9]
    self.defaultOutOf = result[10]
    self.coefficient = result[11]
    self.average = result[12]
    self.max = result[13]
    self.min = result[14]
    self.comment = result[15]

class Averages():

  def __init__(self,result):
    self.pid = result[0]
    self.period_name = result[1]
    self.period_start = result[2]
    self.period_end = result[3]
    self.studentname = result[4]
    self.studentAverage = result[5]
    self.classAverage = result[6]
    self.max = result[7]
    self.min = result[8]
    self.outOf = result[9]
    self.defaultOutOf = result[10]
    self.subject = result[11]

class Periods():

  def __init__(self,result):

    self.pid = result[0]
    self.student = result[1]
    self.periodName = result[2]
    self.periodStart = result[3]
    self.periodEnd = result[4]

class Evaluations():

  def __init__(self,result):
    self.pid = result[0]
    self.period_name = result[1]
    self.period_start = result[2]
    self.period_end = result[3]
    self.studentname = result[4]
    self.eid = result[5]
    self.evalName = result[6]
    self.evalDomain = result[7]
    self.evalTeacher = result[8]
    self.evalCoefficient = result[9]
    self.evalDescription = result[10]
    self.evalSubject = result[11]
    self.evalDate = result[12]
    self.acqId = result[13] 
    self.acqName = result[14]
    self.acqAbbreviation = result[15]
    self.acqLevel = result[16]
    self.acqDomain = result[17]
    self.acqCoefficient = result[18]

class Absences():

  def __init__(self,result):
    self.pid = result[0]
    self.period_name = result[1]
    self.period_start = result[2]
    self.period_end = result[3]
    self.studentname = result[4]
    self.abid = result[5]
    self.absenceFrom = result[6]
    self.absenceTo = result[7]
    self.absenceJustified = result[8]
    self.absenceHours = result[9]
    self.absenceDays = result[10]
    self.absenceReasons = result[11]

class Lessons():

  def __init__(self,result):
    self.lid = result[0]
    self.studentname = result[1]
    self.lessonDateTime = result[2]
    self.lessonStart = result[3]
    self.lessonEnd = result[4]
    self.lessonSubject = result[5]
    self.lessonRoom = result[6]
    self.lessonCanceled = result[7]
    self.lessonStatus = result[8]
    self.lessonNum = result[9]

class Homework():

  def __init__(self,result):
    self.hid = result[0]
    self.studentname = result[1]
    self.homeworkSubject = result[2]
    self.homeworkDescription = result[3]
    self.homeworkDone = result[4]
    self.homeworkDate = result[5]

class Student():

  def __init__(self,result):
    self.sid = result[0]
    self.studentFullname = result[1]
    self.studentSchool = result[2]
    self.studentClass = result[3]
    self.homeworkList = []
    self.evaluationShortList = []
    self.absenceShortList = []
    self.averageList = []    
    self.gradeList = []    
    self.lessonShortList = []
    self.punishmentShortList = []

class Punishments():

  def __init__(self,result):
    self.pid = result[0]
    self.period_name = result[1]
    self.period_start = result[2]
    self.period_end = result[3]
    self.studentname = result[4]
    self.punid = result[5]
    self.punishmentDate = result[6]
    self.punishmentDuringLesson = result[7]
    self.punishmentReasons = result[8]
    self.punishmentCircumstances = result[9]
    self.punishmentNature = result[10]
    self.punishmentDuration = result[11]
    self.punishmentHomework = result[12]   
    self.punishmentExclusion = result[13]