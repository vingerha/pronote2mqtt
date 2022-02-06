#!/usr/bin/env python3
import sqlite3
import os
import logging
import datetime
import json
#from gazpar import TYPE_I,TYPE_P

# Constants
DATABASE_NAME = "pronote2mqtt.db"
DATABASE_TIMEOUT = 10
DATABASE_DATE_FORMAT = "%Y-%m-%d"
DATABASE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Config constants
P2M_KEY = "p2m"
DB_KEY = "db"
INFLUX_KEY = "influx"
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
    self.influxVersion = None
    self.path = path
    self.studentList = []
  
  # Database initialization
  def init(self,p2mVersion,dbVersion,influxVersion):

    # Create table for configuration
    logging.debug("Creation of config table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS config (
                                key TEXT NOT NULL 
                                , value TEXT NOT NULL)''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_config_key
                            ON config (key)''')

    ## Create table of PCEs
    logging.debug("Creation of Period table")
    self.cur.execute('''CREATE TABLE IF NOT EXISTS periods (
                        pid TEXT PRIMARY KEY
                        , name TEXT
                        , start TYPE TEXT
                        , end TYPE TEXT
                        , state TYPE TEXT''')
    self.cur.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_periods_pid
                    ON periods (pid)''')


    # Commit
    self.commit()

    # Update configuration values
    logging.debug("Store configuration")
    self.updateVersion(P2M_KEY, p2mVersion)
    self.updateVersion(DB_KEY, dbVersion)
    self.updateVersion(INFLUX_KEY, influxVersion)
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
  def connect(self,g2mVersion,dbVersion,influxVersion):
    
    # Create directory if not exists
    if not os.path.exists(self.path):
        os.mkdir(self.path)
        logging.debug("Directory %s created",self.path)
    
    # Initialize database if not exists
    if not os.path.exists(self.path + "/" + DATABASE_NAME):
        logging.debug("Initialization of the SQLite database...")
        self.con = sqlite3.connect(self.path + "/" + DATABASE_NAME, timeout=DATABASE_TIMEOUT)
        self.cur = self.con.cursor()
        self.init(g2mVersion,dbVersion,influxVersion)
    else:
        logging.debug("Connexion to database")
        self.con = sqlite3.connect(self.path + "/" + DATABASE_NAME, timeout=DATABASE_TIMEOUT)
        self.cur = self.con.cursor()
        
  # Get measures statistics
  def getPeriodsCount(self,type):

    valueResult = {}
    query = f"SELECT count(*), count(distinct period_start), count(distinct pid), min(period_start), max(period_start) FROM periods'"
    #  to add to distinguish between students.....e.g. WHERE student = '{sid}'"
    self.cur.execute(query)
    queryResult = self.cur.fetchone()
    if queryResult is not None:
            if queryResult[0] is not None:
                valueResult["rows"] = int(queryResult[0])
                valueResult["dates"] = int(queryResult[1])
                valueResult["pid"] = int(queryResult[2])
                valueResult["minDate"] = queryResult[3]
                valueResult["maxDate"] = queryResult[4]
                return valueResult


  # Re-initialize the database
  def reInit(self,p2mVersion,dbVersion,influxVersion):
    
    logging.debug("Reinitialization of the database.")
    
    logging.debug("Drop configuration table")
    self.cur.execute('''DROP TABLE IF EXISTS config''')
    
    logging.debug("Drop Periods table")
    self.cur.execute('''DROP TABLE IF EXISTS periods''')
       
    # Commit work
    self.commit()
    
    # Initialize tables
    self.init(p2mVersion,dbVersion,influxVersion)
      
        
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

    # Load PCEs
    self._loadPce()

    # Load measures
    for myPce in self.pceList:
      self._loadMeasures(myPce)

    # Load thresolds
    for myPce in self.pceList:
      self._loadThresolds(myPce)

  # Load Students
  def _loadStudents(self):

    query = "SELECT * FROM students"
    self.cur.execute(query)
    queryResult = self.cur.fetchall()

    # Create object Student
    for result in queryResult:
      myStudent = Student(result)
      self.studentList.append(myStudent)

# Class Student
class Student():

  def __init__(self,result):

    self.studentId = result[0]
    self.alias = result[1]
    self.activationDate = _convertDateTime(result[2])
    self.frequenceReleve = result[3]
    self.state = result[4]
    self.ownerName = result[5]
    self.postalCode = result[6]
    self.measureList = []
    self.thresoldList = []

# Class Period
class Period():

  def __init__(self,result):

    self.periodId = result[0]
    self.periodName = result[1]
    self.periodStart = _convertDateTime(result[2])
    self.periodEnd = result[3]
  
