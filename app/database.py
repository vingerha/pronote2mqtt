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
                            
    ## Create table of  Periods
    logging.debug("Creation of Students table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS students (
                        sid TEXT PRIMARY KEY
                        , fullname TEXT
                        , school TEXT
                        , class TEXT)''')                          

    ## Create table of  Periods
    logging.debug("Creation of Period table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS periods (
                        pid TEXT PRIMARY KEY
                        , studentname TEXT
                        , name TEXT
                        , start TEXT
                        , end TEXT)''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_periods_pid
                    ON periods (pid)''')

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
                        , max TYPE TEXT
                        , min_of TYPE TEXT
                        , PRIMARY KEY (pid,gid,subject))''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_grades_gid
                    ON grades (pid,gid)''')

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
			, PRIMARY KEY(pid,studentname,subject))''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_averages_pid
                    ON averages (pid,studentname,subject)''')

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
                        , coefficient TXT
                        , description TEXT
                        , subject TEXT
                        , date TEXT
                        , aid TEXT
                        , acquisition_name TEXT
                        , acquisition_level TEXT
                        , acquisition_coefficient TEXT
                        , PRIMARY KEY(pid,eid,aid))''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_evaluations_pideid
                    ON evaluations (pid,eid,aid)''')
   
    # using key on period id and evalid
    logging.debug("Creation of Lessons table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS lessons (
                        lid TEXT NOT NULL
                        , studentname TEXT NOT NULL
                        , lessonDateTime TEXT
                        , lessonStart TEXT
                        , lessonEnd TEXT
                        , lessonSubject TEXT
                        , lessonRoom TEXT
                        , lessonCanceled TEXT
                        , lessonStatus TEXT
                        , PRIMARY KEY(lid,studentname))''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_lessons_lid
                    ON lessons (lid,studentname)''')

    # using key on period id and evalid
    logging.debug("Creation of Homework table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS homework (
                        hid TEXT NOT NULL
                        , studentname TEXT NOT NULL
                        , homeworkSubject TEXT
                        , homeworkDescription TEXT
                        , homeworkDone TEXT
                        , homeworkDate TEXT
                        , PRIMARY KEY(hid,studentname))''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_homework_hid
                    ON homework (hid,studentname)''')


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
        self._loadEvaluationsShort(myStudent)
     
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
    # use the firstname to query the database
    # to improve: make name-format same across tables
    studentfirst=student.studentFullname.split(" ",1)[1]
    query = f"SELECT * FROM homework WHERE studentname like '{studentfirst}'"
    self.cur.execute(query)
    queryResult = self.cur.fetchall()
    # Create object Homework
    for result in queryResult:
      myHomework = Homework(result)
      student.homeworkList.append(myHomework)

  def _loadEvaluationsShort(self,student):
    # use the firstname to query the database
    # to improve: make name-format same across tables
    studentfirst=student.studentFullname.split(" ",1)[1]
    # not collecting all 
    datestart = datetime.date.today() - relativedelta(days=20)
    datestart = datestart.strftime("%Y/%m/%d")
    query = f"SELECT * FROM evaluations WHERE studentname like '{studentfirst}' and date >= '{datestart}' ORDER by date"
    self.cur.execute(query)
    queryResult = self.cur.fetchall()
    # Create object Homework
    for result in queryResult:
      myEvaluation = Evaluations(result)
      student.evaluationShortList.append(myEvaluation)



# class Grades...probably not needed as defined in separate pronote_eveline....py
class Grades():

  def __init__(self,result):

    self.pid = result[0]
    self.period_name = result[1]
    self.period_start = result[2]
    self.period_end = result[3]
    self.gid = result[4]
    self.student = result[5]
    self.date = result[6]
    self.subject = _convertDateTime(result[7])
    self.grade = result[8]
    self.outOf = result[9]
    self.defaultOutOf = result[10]
    self.coefficient = result[11]
    self.average = result[12]
    self.max = result[13]
    self.min - result[14]

class Averages():

  def __init__(self,result):
    self.pid = result[0]
    self.period_name = result[1]
    self.period_start = result[2]
    self.period_end = result[3]
    self.studentname = result[4]
    self.student = result[5]
    self.classAverage = result[6]
    self.max = _convertDateTime(result[7])
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
    self.acqLevel = result[15]
    self.acqCoefficient = result[16]

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
   