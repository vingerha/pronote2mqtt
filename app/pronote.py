import pronotepy
from pronotepy import ent
import os
import datetime               
from datetime import date
from datetime import timedelta 
import json
import logging
import math

from pronotepy.ent import *
import requests
from requests.adapters import TimeoutSauce

#Hardcoded (to be improved)
lessonDays=15
homeworkDays=15


class MyTimeout(TimeoutSauce):
    def __init__(self, *args, **kwargs):
        if kwargs['connect'] is None:
            kwargs['connect'] = 5 # change here for different connection timeout
        if kwargs['read'] is None:
            kwargs['read'] = 5 # change here for different read timeout
        super(MyTimeout, self).__init__(*args, **kwargs)

requests.adapters.TimeoutSauce = MyTimeout

class Pronote:
    def __init__(self):
        
        # Initialize instance variables
        self.studentname = None
        self.session = None
        self.auth_nonce = None
        self.gradeList = []
        self.averageList = []
        self.periodList = []
        self.evalList = []
        self.lessonList = []
        self.homeworkList = []
        self.studentList = []
        self.absenceList = []
        self.punishmentList = []
        self.whoiam = None
        self.isConnected = False
        
    def getData(self,prefix_url,username,password,cas,GradeAverage,parent,fullname):
        self.isConnected = False
        if cas:
            _ent = getattr(ent, cas)
        else:
            _ent = ''
        if parent:
            client = pronotepy.ParentClient('https://'+prefix_url+'.index-education.net/pronote/parent.html', username, password, _ent)
        else:
            client = pronotepy.Client('https://'+prefix_url+'.index-education.net/pronote/eleve.html', username, password, _ent)
            
        if client.logged_in:
           self.isConnected = True
        else:
           logging.error("Error while authenticating when calling")
           return
        
        if fullname:
            client.set_child(fullname)       
        
        jsondata = {}
        
        #Student
        logging.info("Collecting Student---------------------------------------------------")
        jsondata['students'] = []
        identity = client.parametres_utilisateur
        
        # setting studentname, used for further actions
        self.studentname = client.parametres_utilisateur["donneesSec"]["donnees"]["ressource"]["L"]
        self.studentname = self.studentname.replace(' ', '_')
        
        jsondata['students'].append({
            'sid': client.parametres_utilisateur["donneesSec"]["donnees"]["ressource"]["N"],
            'studentFullname': client.parametres_utilisateur["donneesSec"]["donnees"]["ressource"]["L"],
            'studentSchool': client.parametres_utilisateur["donneesSec"]["donnees"]["ressource"]["Etablissement"]["V"]["L"],
            'studentClass': client.parametres_utilisateur["donneesSec"]["donnees"]["ressource"]["classeDEleve"]["L"],
        })
        studentList = jsondata

        if studentList:
           for student in studentList["students"]:
               myStudent = Student(self.studentname, student)
               self.addStudent(myStudent)
        else:
            logging.error("Student list is empty")
        
        #get grades/averages, this does not apply to all children (new system > evaluations)
        periods = client.periods
        if GradeAverage:
            logging.info("Collecting Grades ---------------------------------------------------")
#grades     
            periods = client.periods               
            jsondata['grades'] = []
            for period in periods:
                for grade in period.grades:
            #data in order: id, date, subject(course),grade,out_of,default_out_of,coefficient,average(class),max,min 
                    jsondata['grades'].append({
                        'pid': period.id,
                        'periodName': period.name,
                        'periodStart': period.start.strftime("%Y/%m/%d"),
                        'periodEnd': period.end.strftime("%Y/%m/%d"),
                        'gid': grade.id,
                        'date': grade.date.strftime("%Y/%m/%d"),
                        'subject': grade.subject.name,
                        'grade': grade.grade,            
                        'outOf': grade.out_of,
                        'defaultOutOf': grade.grade+' / '+grade.out_of,
                        'coefficient': grade.coefficient,
                        'average': grade.average,           
                        'max': grade.max,
                        'min': grade.min,
                        'comment': grade.comment,
                })
            gradeList = jsondata

            if gradeList:
               for grade in gradeList["grades"]:
                   myGrade = Grade(self.studentname, grade) 
                   self.addGrade(myGrade)
            else:
               logging.error("Grade list is empty")
#averages
            logging.info("Collecting Averages---------------------------------------------------")
            periods = client.periods
            jsondata['averages'] = []
            for period in periods:
                for average in period.averages:
            #data in order: id, date, subject(course),grade,out_of,default_out_of,coefficient,average(class),max,min
                    jsondata['averages'].append({
                        'pid': period.id,
                        'periodName': period.name,
                        'periodStart': period.start.strftime("%Y/%m/%d"),
                        'periodEnd': period.end.strftime("%Y/%m/%d"),
                        'student': average.student,
                        'classAverage': average.class_average,
                        'max': average.max,
                        'min': average.min,
                        'outOf': average.out_of,
                        'defaultOutOf': average.student+' / '+average.out_of,
                        'subject': average.subject.name,
                })
            averageList = jsondata
            if averageList:
               for average in averageList["averages"]:
                   myAverage = Average(self.studentname,average)
                   self.addAverage(myAverage)
            else:
               logging.error("Average list is empty")
  
        else:
            logging.info("Skipping Grades and Averages---------------------------------------------------")

#periods
        logging.info("Collecting Periods---------------------------------------------------")
        periods = client.periods
        jsondata['periods'] = []
        for period in periods:
            jsondata['periods'].append({
                'pid': period.id,
                'periodName': period.name,
                'periodStart': period.start.strftime("%Y/%m/%d"),
                'periodEnd': period.end.strftime("%Y/%m/%d"),
        })
        periodList = jsondata
        if periodList:
           for period in periodList["periods"]:
               myPeriod = Period(self.studentname,period)
               self.addPeriod(myPeriod)
        else:
            logging.error("Period list is empty") 

#evaluations
        if not GradeAverage:
            logging.info("Collecting Evaluations---------------------------------------------------")
            periods = client.periods
            jsondata['evaluations'] = []
            for period in periods:
                for eval in period.evaluations:
                    for acq in eval.acquisitions:
                        jsondata['evaluations'].append({
                            'pid': period.id,
                            'periodName': period.name,
                            'periodStart': period.start.strftime("%Y/%m/%d"),
                            'periodEnd': period.end.strftime("%Y/%m/%d"),
                            'eid': eval.id,
                            'evalName': eval.name,
                            'evalDomain': eval.domain,
                            'evalTeacher': eval.teacher,
                            'evalCoefficient': eval.coefficient,
                            'evalDescription': eval.description,
                            'evalSubject': eval.subject.name,
                            'evalDate': eval.date.strftime("%Y/%m/%d"),
                            'acqId': acq.order,
                            'acqName': acq.name,
                            'acqAbbreviation': acq.abbreviation,
                            'acqLevel': acq.level,
                            'acqDomain': acq.domain,
                            'acqCoefficient': acq.coefficient,
                })
            evalList = jsondata
            if evalList:
               for eval in evalList["evaluations"]:
                   myEval = Evaluation(self.studentname,eval)
                   self.addEval(myEval)
            else:
                logging.error("Evaluations list is empty")
        else:
            logging.info("Skipping Averages---------------------------------------------------")
            

#absences
        logging.info("Collecting Absences---------------------------------------------------")
        periods = client.periods
        jsondata['absences'] = []
        for period in periods:
            for absence in period.absences:
                jsondata['absences'].append({
                    'pid': period.id,
                    'periodName': period.name,
                    'periodStart': period.start.strftime("%Y/%m/%d"),
                    'periodEnd': period.end.strftime("%Y/%m/%d"),
                    'abid': absence.id,
                    'absenceFrom': absence.from_date.strftime("%Y/%m/%d %H:%M"),
                    'absenceTo': absence.to_date.strftime("%Y/%m/%d %H:%M"),
                    'absenceJustified': absence.justified,
                    'absenceHours': absence.hours,
                    'absenceDays': absence.days,
                    'absenceReasons': absence.reasons,
                })
        absenceList = jsondata
        if absenceList:
           for absence in absenceList["absences"]:
               myAbsence = Absence(self.studentname,absence)
               self.addAbsence(myAbsence)
        else:
            logging.error("Absence list is empty")
            
#Lessons
        logging.info("Collecting Lessons---------------------------------------------------")

        jsondata['lessons'] = []
        index = 0
        dateLesson = date.today()
        #Get lessons over X period
        while index <= lessonDays:
            lessons = client.lessons(dateLesson)
            for lesson in lessons:
                try:
                    jsondata['lessons'].append({
                        'lid': lesson.id,
                        'lessonDateTime': lesson.start.strftime("%Y/%m/%d %H:%M"),
                        'lessonStart': lesson.start.strftime("%H:%M"),
                        'lessonEnd': lesson.end.strftime("%H:%M"),
                        'lessonSubject': lesson.subject.name,
                        'lessonRoom': lesson.classroom,
                        'lessonCanceled': lesson.canceled,
                        'lessonStatus': lesson.status,
                        'lessonNum': lesson.num,
                })
                except AttributeError:
                    jsondata['lessons'].append({
                        'lid': lesson.id,
                        'lessonDateTime': lesson.start.strftime("%Y/%m/%d %H:%M"),
                        'lessonStart': lesson.start.strftime("%H:%M"),
                        'lessonEnd': lesson.end.strftime("%H:%M"),
                        'lessonSubject': "ereur_nom",
                        'lessonRoom': lesson.classroom,
                        'lessonCanceled': lesson.canceled,
                        'lessonStatus': lesson.status,
                        'lessonNum': lesson.num,
                })    
            index += 1
            dateLesson = dateLesson + timedelta(days = 1)
        lessonList = jsondata
        if lessonList:
           for lesson in lessonList["lessons"]:
               myLesson = Lesson(self.studentname,lesson)
               self.addLesson(myLesson)
        else:
            logging.error("Average list is empty")
            
            
#Homework
        logging.info("Collecting Homework---------------------------------------------------")
        jsondata['homework'] = []
        index = 0
        dateHomework = date.today()
        #Get lessons over X period
        while index <= homeworkDays:
            homework = client.homework(dateHomework)
            for hw in homework:
                jsondata['homework'].append({
                    'hid': hw.id,
                    'homeworkSubject': hw.subject.name,
                    'homeworkDescription': hw.description,
                    'homeworkDone': hw.done,
                    'homeworkDate': hw.date.strftime("%Y/%m/%d"),
            })
            index += 1
            dateHomework = dateHomework + timedelta(days = 1)
        homeworkList = jsondata
        if homeworkList:

           for homework in homeworkList["homework"]:
               myHomework = Homework(self.studentname,homework)
               self.addHomework(myHomework)

        else:
            logging.error("Homework list is empty")
                        
#punishments
        logging.info("Collecting Punishments---------------------------------------------------")
        periods = client.periods
        jsondata['punishments'] = []
        try: 
            for period in periods:
                    for punishment in period.punishments:         
                            jsondata['punishments'].append({
                                'pid': period.id,
                                'periodName': period.name,
                                'periodStart': period.start.strftime("%Y/%m/%d"),
                                'periodEnd': period.end.strftime("%Y/%m/%d"),
                                'punid': punishment.id,
                                'punishmentDate': punishment.given.strftime("%Y/%m/%d"),
                                'punishmentDuringLesson': punishment.during_lesson,
                                'punishmentReasons': punishment.reasons,
                                'punishmentCircumstances': punishment.circumstances,
                                'punishmentNature': punishment.nature,
                                'punishmentDuration': str(punishment.duration),
                                'punishmentHomework': punishment.homework,
                                'punishmentExclusion': punishment.exclusion,                    
                        })
        except:
            logging.error("Error getting punishments from pronotepy")
            
        punishmentList = jsondata
        #print(punishmentList)
        if punishmentList:
           for punishment in punishmentList["punishments"]:
               myPunishment = Punishment(self.studentname,punishment)
               self.addPunishment(myPunishment)
        else:
            logging.error("Punishment list is empty")            
               
    def addPeriod(self,period):
        self.periodList.append(period)
        
    def addGrade(self,grade):
        self.gradeList.append(grade)

    def addAverage(self,average):
        self.averageList.append(average)    

    def addLesson(self,lesson):
        self.lessonList.append(lesson)
        
    def addEval(self,eval):
        self.evalList.append(eval)    

    def addHomework(self,homework):
        self.homeworkList.append(homework)

    def addStudent(self,student):
        self.studentList.append(student)
        
    def addAbsence(self,absence):
        self.absenceList.append(absence)        
        
    def addPunishment(self,punishment):
        self.punishmentList.append(punishment) 
        
class Grade:
    
    # Constructor
    def __init__(self, studentname, grade):
        
        # Init attributes
        self.pid = None
        self.periodName = None
        self.periodStart = None
        self.periodEnd = None
        self.gid = None
        self.student = None
        self.date = None
        self.subject = None
        self.grade = None
        self.outOf = None
        self.defaultOutOf = None
        self.coefficient = None
        self.average = None
        self.max = None
        self.min = None
        self.comment = None

        self.pid = grade["pid"]
        self.periodName = grade["periodName"]
        self.periodStart = grade["periodStart"]
        self.periodEnd = grade["periodEnd"]
        self.gid = grade["gid"]
        self.student = studentname
        self.date = grade["date"]
        self.subject = grade["subject"]
        self.grade = grade["grade"]
        self.outOf = grade["outOf"]
        self.defaultOutOf = grade["defaultOutOf"]
        self.coefficient = grade["coefficient"]
        self.average = grade["average"]
        self.max = grade["max"]
        self.min =  grade["min"]
        self.comment =  grade["comment"]


    # Store measure to database
    def store(self,db):

        dbTable = "grades"

        if dbTable:
            logging.debug("Store grades %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s",self.pid,self.periodName,self.periodStart,self.periodEnd, \
                          self.gid,self.student,str(self.date),self.subject,self.grade,self.outOf,self.defaultOutOf,self.coefficient,self.average,self.max,self.min, self.comment)
            grade_query = f"INSERT OR REPLACE INTO grades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            db.cur.execute(grade_query, [self.pid,self.periodName,self.periodStart,self.periodEnd,self.gid,self.student,self.date,self.subject,self.grade,self.outOf,self.defaultOutOf,self.coefficient,self.average,self.max,self.min,self.comment])

class Average:

    # Constructor
    def __init__(self, studentname, average):

        # Init attributes
        self.pid = None
        self.periodName = None
        self.periodStart = None
        self.periodEnd = None
        self.studentname = None
        self.student = None
        self.classAverage = None
        self.max = None
        self.min = None
        self.outOf = None
        self.defaultOutOf = None
        self.subject = None

        self.pid = average["pid"]
        self.periodName = average["periodName"]
        self.periodStart = average["periodStart"]
        self.periodEnd = average["periodEnd"]
        self.studentname = studentname
        self.student = average["student"]
        self.classAverage = average["classAverage"]
        self.max = average["max"]
        self.min = average["min"]
        self.outOf = average["outOf"]
        self.defaultOutOf = average["defaultOutOf"]
        self.subject = average["subject"]

    # Store measure to database
    def store(self,db):

        dbTable = "averages"

        if dbTable:
            logging.debug("Store averages %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s",self.pid,self.periodName,self.periodStart,self.periodEnd,self.studentname,self.student,self.classAverage,self.max,self.min, \
                         self.outOf,self.defaultOutOf,self.subject)
            average_query = f"INSERT OR REPLACE INTO averages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            db.cur.execute(average_query, [self.pid,self.periodName,self.periodStart,self.periodEnd,self.studentname,self.student,self.classAverage,self.max,self.min,self.outOf,self.defaultOutOf,self.subject])

class Evaluation:

    # Constructor
    def __init__(self, studentname, eval):

        # Init attributes
        self.pid = None
        self.periodName = None
        self.periodStart = None
        self.periodEnd = None
        self.studentname = None
        self.eid = None
        self.evalName = None
        self.evalDomain = None
        self.evalTeacher = None
        self.evalCoefficient = None
        self.evalDescription = None
        self.evalSubject = None
        self.evalDate = None
        self.acquisitionId = None
        self.acquisitionName = None
        self.acquisitionAbbreviation = None
        self.acquisitionLevel = None
        self.acquisitionDomain = None
        self.acquisitionCoefficient = None
        
        self.pid = eval["pid"]
        self.periodName = eval["periodName"]
        self.periodStart = eval["periodStart"]
        self.periodEnd = eval["periodEnd"]
        self.studentname= studentname
        self.eid = eval["eid"]
        self.evalName = eval["evalName"]
        self.evalDomain = eval["evalDomain"]
        self.evalTeacher = eval["evalTeacher"]
        self.evalCoefficient = eval["evalCoefficient"]
        self.evalDescription = eval["evalDescription"]
        self.evalSubject = eval["evalSubject"]
        self.evalDate = eval["evalDate"]
        self.acquisitionId = eval["acqId"]
        self.acquisitionName = eval["acqName"]
        self.acquisitionAbbreviation = eval["acqAbbreviation"]
        self.acquisitionLevel = eval["acqLevel"]
        self.acquisitionDomain = eval["acqDomain"]
        self.acquisitionCoefficient = eval["acqCoefficient"]

    # Store measure to database
    def store(self,db):

        dbTable = "evaluations"

        if dbTable:
            logging.debug("Store evaluations %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s",self.pid,self.periodName,self.periodStart,self.periodEnd,self.studentname,self.eid,self.evalName,self.evalDomain,self.evalTeacher,self.evalCoefficient,self.evalDescription,self.evalSubject,self.evalDate,self.acquisitionId,self.acquisitionName,self.acquisitionAbbreviation,self.acquisitionLevel,self.acquisitionDomain,self.acquisitionCoefficient)
            eval_query = f"INSERT OR REPLACE INTO evaluations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            db.cur.execute(eval_query, [self.pid,self.periodName,self.periodStart,self.periodEnd,self.studentname,self.eid,self.evalName,self.evalDomain,self.evalTeacher,\
                          self.evalCoefficient,self.evalDescription,self.evalSubject,self.evalDate,self.acquisitionId,self.acquisitionName,self.acquisitionAbbreviation,self.acquisitionLevel,self.acquisitionDomain,self.acquisitionCoefficient])

class Lesson:

    # Constructor
    def __init__(self, studentname, lesson):

        # Init attributes
        self.lid = None
        self.studentname = None
        self.lessonDateTime = None
        self.lessonStart = None
        self.lessonEnd = None
        self.lessonSubject = None
        self.lessonRoom = None
        self.lessonCanceled = None
        self.lessonStatus = None
        self.lessonNum = None

        self.lid = lesson["lid"]
        self.studentname= studentname
        self.lessonDateTime = lesson["lessonDateTime"]
        self.lessonStart = lesson["lessonStart"]
        self.lessonEnd = lesson["lessonEnd"]
        self.lessonSubject = lesson["lessonSubject"]
        self.lessonRoom = lesson["lessonRoom"]
        self.lessonCanceled = lesson["lessonCanceled"]
        self.lessonStatus = lesson["lessonStatus"]
        self.lessonNum = lesson["lessonNum"]

    # Store measure to database
    def store(self,db):

        dbTable = "lessons"

        if dbTable:
            logging.debug("Store lessons %s, %s, %s, %s, %s, %s, %s, %s, %s, %s",self.lid,self.studentname,self.lessonDateTime,self.lessonStart,self.lessonEnd,self.lessonSubject,self.lessonRoom,self.lessonCanceled,self.lessonStatus,self.lessonNum)
            lesson_query = f"INSERT OR REPLACE INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            db.cur.execute(lesson_query, [self.lid,self.studentname,self.lessonDateTime,self.lessonStart,self.lessonEnd,self.lessonSubject,self.lessonRoom,self.lessonCanceled,self.lessonStatus,self.lessonNum])



class Period:

    # Constructor
    def __init__(self, studentname, period):

        # Init attributes
        self.pid = None
        self.student = None
        self.periodName = None
        self.periodStart = None
        self.periodEnd = None

        self.pid = period["pid"]
        self.student = studentname
        self.periodName = period["periodName"]
        self.periodStart = period["periodStart"]
        self.periodEnd = period["periodEnd"]

    # Store measure to database
    def store(self,db):

        dbTable = "periods"

        if dbTable:
            logging.debug("Store periods %s, %s, %s, %s, %s",self.pid,self.student,self.periodName,self.periodStart,self.periodEnd)
            period_query = f"INSERT OR REPLACE INTO periods VALUES (?, ?, ?, ?, ?)"
            db.cur.execute(period_query, [self.pid,self.student,self.periodName,self.periodStart,self.periodEnd])

class Homework:

    # Constructor
    def __init__(self,studentname,homework):

        # Init attributes
        self.hid = None
        self.studentname = None
        self.homeworkSubject = None
        self.homeworkDescription = None
        self.homeworkDone = None
        self.homeworkDate = None

        self.hid = homework["hid"]
        self.studentname = studentname
        self.homeworkSubject = homework["homeworkSubject"]
        self.homeworkDescription = homework["homeworkDescription"]
        self.homeworkDone = homework["homeworkDone"]
        self.homeworkDate = homework["homeworkDate"]

    # Store measure to database
    def store(self,db):

        dbTable = "homework"

        if dbTable:
            logging.debug("Store homework %s, %s, %s, %s, %s, %s",self.hid,self.studentname,self.homeworkSubject,self.homeworkDescription,self.homeworkDone,self.homeworkDate)
            homework_query = f"INSERT OR REPLACE INTO homework VALUES (?, ?, ?, ?, ?, ?)"
            db.cur.execute(homework_query, [self.hid,self.studentname,self.homeworkSubject,self.homeworkDescription,self.homeworkDone,self.homeworkDate])

class Student:

    # Constructor
    def __init__(self,studentname, student):

        # Init attributes
        self.sid = None
        self.studentFullname = None
        self.studentSchool = None
        self.studentClass = None

        self.sid = student["sid"]
        self.studentFullname = studentname
        self.studentSchool = student["studentSchool"]
        self.studentClass = student["studentClass"]

    # Store measure to database
    def store(self,db):

        dbTable = "students"

        if dbTable:
            logging.debug("Store student %s, %s, %s, %s",self.sid,self.studentFullname,self.studentSchool,self.studentClass)
            student_query = f"INSERT OR REPLACE INTO students VALUES (?, ?, ?, ?)"
            db.cur.execute(student_query, [self.sid,self.studentFullname,self.studentSchool,self.studentClass])
            
class Absence:

    # Constructor
    def __init__(self, studentname, absence):

        # Init attributes
        self.pid = None
        self.periodName = None
        self.periodStart = None
        self.periodEnd = None
        self.studentname = None
        self.abid = None
        self.absenceFrom = None
        self.absenceTo = None
        self.absenceJustified = None
        self.absenceHours = None
        self.absenceDays = None
        self.absenceReasons = None

        self.pid = absence["pid"]
        self.periodName = absence["periodName"]
        self.periodStart = absence["periodStart"]
        self.periodEnd = absence["periodEnd"]
        self.studentname= studentname
        self.abid = absence["abid"]
        self.absenceFrom = absence["absenceFrom"]
        self.absenceTo = absence["absenceTo"]
        self.absenceJustified = absence["absenceJustified"]
        self.absenceHours = absence["absenceHours"]
        self.absenceDays = absence["absenceDays"]
        # make string form 'reasons' (as it is a list)
        self.absenceReasons = ' '.join(absence["absenceReasons"])


    # Store measure to database
    def store(self,db):

        dbTable = "absences"

        if dbTable:
            logging.debug("Store absences %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s",self.pid,self.periodName,self.periodStart,self.periodEnd,self.studentname,self.abid,self.absenceFrom,self.absenceTo,self.absenceJustified,self.absenceHours,self.absenceDays,self.absenceReasons)
            absence_query = f"INSERT OR REPLACE INTO absences VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            db.cur.execute(absence_query, [self.pid,self.periodName,self.periodStart,self.periodEnd,self.studentname,self.abid,self.absenceFrom,self.absenceTo,self.absenceJustified,self.absenceHours,self.absenceDays,self.absenceReasons])            
            
            
            
class Punishment:

    # Constructor
    def __init__(self, studentname, punishment):

        # Init attributes
        self.pid = None
        self.period_name = None
        self.period_start = None
        self.period_end = None
        self.studentname = None
        self.punid = None
        self.punishmentDate = None
        self.punishmentDuringLesson = None
        self.punishmentCircumstances = None
        self.punishmentNature = None
        self.punishmentDuration = None
        self.punishmentHomework = None
        self.punishmentExclusion = None
        
        self.pid = punishment["pid"]
        self.periodName = punishment["periodName"]
        self.periodStart = punishment["periodStart"]
        self.periodEnd = punishment["periodEnd"]
        self.studentname = studentname
        self.punid = punishment["punid"]
        self.punishmentDate = punishment["punishmentDate"]
        self.punishmentDuringLesson = punishment["punishmentDuringLesson"]
        self.punishmentReasons = ' '.join(punishment["punishmentReasons"])
        self.punishmentCircumstances = punishment["punishmentCircumstances"]
        self.punishmentNature = punishment["punishmentNature"]
        self.punishmentDuration = punishment["punishmentDuration"]
        self.punishmentHomework = punishment["punishmentHomework"]
        self.punishmentExclusion = punishment["punishmentExclusion"]
        
    # Store measure to database
    def store(self,db):

        dbTable = "punishments"

        if dbTable:
#            logging.debug("Store punishments %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s",self.pid,self.periodName,self.periodStart,self.periodEnd,self.studentname,self.punid,self.punishmentDate,self.punishmentDuringLesson,self.punishmentCircumstances,self.punishmentNature,self.punishmentHomework,self.punishmentExclusion)
            punishment_query = f"INSERT OR REPLACE INTO punishments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            db.cur.execute(punishment_query, [self.pid,self.periodName,self.periodStart,self.periodEnd,self.studentname,self.punid,self.punishmentDate,self.punishmentDuringLesson,self.punishmentReasons,self.punishmentCircumstances,self.punishmentNature,self.punishmentDuration,self.punishmentHomework,self.punishmentExclusion])                      
             