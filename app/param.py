#!/usr/bin/env python3

import argparse
import os
import logging

def _isItTrue(val):
  
  if val.lower() == 'true':
    return True
  else:
    return False

  
# Class Params
class Params:
  
  # Constructor
  def __init__(self):
    
    # Step 1 : set default params
    
    # Pronote params child 1 (setup to support 2 children, see pronote2mqtt.py)
    # as pronoteStudent_1 (or 2) use the firstname only, for 'demo' the username in pronote is 'PARENT Fanny', hence use: 'fanny'
    self.pronoteStudent_1 = 'fanny'
    self.pronoteUsername_1 = 'demonstration'
    self.pronotePassword_1 = 'pronotevs'
    self.pronotePrefixUrl_1 = 'demo'
    self.pronoteEnt_1 = True
    self.pronoteCas_1 = ""
    self.pronoteGradesAverages_1 = True
    
    self.pronoteStudent_2 = ''
    self.pronoteUsername_2 = ''
    self.pronotePassword_2 = ''
    self.pronotePrefixUrl_2 = ''
    self.pronoteEnt_2 = True
    self.pronoteCas_2 = ''
    self.pronoteGradesAverages_2 = False
    
    # Mqtt params
    self.mqttHost = ''
    self.mqttPort = 1883
    self.mqttClientId = 'pronote2mqtt'
    self.mqttUsername = ''
    self.mqttPassword = ''
    self.mqttQos = 1
    self.mqttTopic = 'pronote'
    self.mqttRetain = True
    self.mqttSsl = False
    
    
    # Run params
    self.scheduleTime = '06:00'
    
    # Publication params
    self.hassDiscovery = True
    self.hassPrefix = 'homeassistant'
    self.hassDeviceName = 'pronote'
    self.hassPeriodSensor = True
    self.hassPeriodSensorCount = 10
    
    # Database params
    self.dbInit = True
    self.dbPath = './data'
    
    # Debug params
    self.debug = False
    
    # Step 2 : Init arguments for command line
    self.args = self.initArg()
     
    # Step 3 : Get args from command line and overwrite env if needed
    self.getFromArgs()
    
    
  # Set arguments list
  def initArg(self):
    
    self.parser = argparse.ArgumentParser()
    self.parser.add_argument(
        "--pronote_student_1",    help="PRONOTE student name, ex : 'name'")
    self.parser.add_argument(
        "--pronote_username_1",    help="PRONOTE user name, ex : 'first.last'")
    self.parser.add_argument(
        "--pronote_password_1",    help="PRONOTE password")
    self.parser.add_argument(
        "--pronote_prefixurl_1",    help="PRONOTE prefix url")
    self.parser.add_argument(
        "--pronote_ent_1",    help="PRONOTE ent")
    self.parser.add_argument(
        "--pronote_cas_1",    help="PRONOTE case")
    
    self.parser.add_argument(
        "--pronote_student_2",    help="PRONOTE student name, ex : 'name'")
    self.parser.add_argument(
        "--pronote_username_2",    help="PRONOTE user name, ex : myemail@email.com")
    self.parser.add_argument(
        "--pronote_password_2",    help="PRONOTE password")
    self.parser.add_argument(
        "--pronote_prefixurl_2",    help="PRONOTE prefix url")
    self.parser.add_argument(
        "--pronote_ent_2",    help="PRONOTE ent")
    self.parser.add_argument(
        "--pronote_cas_2",    help="PRONOTE case")    
        
    self.parser.add_argument(
        "-s", "--schedule",   help="Schedule the launch of the script at hh:mm everyday")
    self.parser.add_argument(
        "--mqtt_host",        help="Hostname or ip adress of the Mqtt broker")
    self.parser.add_argument(
        "--mqtt_port",        help="Port of the Mqtt broker")
    self.parser.add_argument(
        "--mqtt_clientId",    help="Client Id to connect to the Mqtt broker")
    self.parser.add_argument(
        "--mqtt_username",    help="Username to connect to the Mqtt broker")
    self.parser.add_argument(
        "--mqtt_password",    help="Password to connect to the Mqtt broker")
    self.parser.add_argument(
        "--mqtt_qos",         help="QOS of the messages to be published to the Mqtt broker")
    self.parser.add_argument(
        "--mqtt_topic",       help="Topic prefix of the messages to be published to the Mqtt broker")
    self.parser.add_argument(
        "--mqtt_retain",      help="Retain flag of the messages to be published to the Mqtt broker, possible values : True or False")
    self.parser.add_argument(
        "--mqtt_ssl",         help="Enable MQTT SSL connexion, possible values : True or False")
    
    self.parser.add_argument(
        "--hass_discovery",   help="Enable Home Assistant discovery, possible values : True or False")
    self.parser.add_argument(
        "--hass_prefix",      help="Home Assistant discovery Mqtt topic prefix")
    self.parser.add_argument(
        "--hass_device_name", help="Home Assistant device name")
    self.parser.add_argument(
        "--db_init", help="Force database reinitialization : True or False")
    self.parser.add_argument(
        "--db_path", help="Database path (default : /data")

    self.parser.add_argument(
        "--debug",            help="Enable debug mode")
    
    return self.parser.parse_args() 
  
  # Get params from arguments in command line
  def getFromArgs(self):
    
    if self.args.pronote_student_1 is not None: self.pronoteStudent_1 = self.args.pronote_student_1
    if self.args.pronote_username_1 is not None: self.pronoteUsername_1 = self.args.pronote_username_1
    if self.args.pronote_password_1 is not None: self.pronotePassword_1 = self.args.pronote_password_1
    if self.args.pronote_prefixurl_1 is not None: self.pronotePrefixUrl_1 = self.args.pronote_prefixurl_1
    if self.args.pronote_ent_1 is not None: self.pronoteEnt_1 = self.args.pronote_end_1
    if self.args.pronote_cas_1 is not None: self.pronotePassword_1 = self.args.pronote_cas_1
    
    if self.args.pronote_student_2 is not None: self.pronoteStudent_2 = self.args.pronote_student_2
    if self.args.pronote_username_2 is not None: self.pronoteUsername_2 = self.args.pronote_username_2
    if self.args.pronote_password_2 is not None: self.pronotePassword_2 = self.args.pronote_password_2
    if self.args.pronote_prefixurl_2 is not None: self.pronotePrefixUrl_2 = self.args.pronote_prefixurl_2
    if self.args.pronote_ent_2 is not None: self.pronoteEnt_2 = self.args.pronote_end_2
    if self.args.pronote_cas_2 is not None: self.pronotePassword_2 = self.args.pronote_cas_2

    
    if self.args.mqtt_host is not None: self.mqttHost = self.args.mqtt_host
    if self.args.mqtt_port is not None: self.mqttPort = int(self.args.mqtt_port)
    if self.args.mqtt_clientId is not None: self.mqttClientId = self.args.mqtt_clientId
    if self.args.mqtt_username is not None: self.mqttUsername = self.args.mqtt_username
    if self.args.mqtt_password is not None: self.mqttPassword = self.args.mqtt_password
    if self.args.mqtt_qos is not None: self.mqttQos = int(self.args.mqtt_qos)
    if self.args.mqtt_topic is not None: self.mqttTopic = self.args.mqtt_topic
    if self.args.mqtt_retain is not None: self.mqttRetain = _isItTrue(self.args.mqtt_retain)
    if self.args.mqtt_ssl is not None: self.mqttSsl = _isItTrue(self.args.mqtt_ssl)
      
    if self.args.schedule is not None: self.scheduleTime = self.args.schedule
      
    
    if self.args.hass_discovery is not None: self.hassDiscovery = _isItTrue(self.args.hass_discovery)
    if self.args.hass_prefix is not None: self.hassPrefix = self.args.hass_prefix
    if self.args.hass_device_name is not None: self.hassDeviceName = self.args.hass_device_name
            
    if self.args.db_init is not None: self.dbInit = _isItTrue(self.args.db_init)
    if self.args.db_path is not None: self.db_path = self.args.db_path
    
    if self.args.debug is not None: self.debug = _isItTrue(self.args.debug)
    
    
  # Check parameters
  def checkParams(self):
    if self.pronoteStudent_1 is None:
      logging.error("Parameter PRONOTE username is mandatory.")
      return False
    elif self.pronoteUsername_1 is None:
      logging.error("Parameter PRONOTE username is mandatory.")
      return False
    elif self.pronotePassword_1 is None:
      logging.error("Parameter PRONOTE password is mandatory.")
      return False
    elif self.pronotePrefixUrl_1 is None:
      logging.error("Parameter PRONOTE prefixurl is mandatory.")
      return False
    elif self.mqttHost is None:
      logging.error("Parameter MQTT host is mandatory.")
      return False
    else:
      if self.hassDiscovery == False:
        logging.warning("Home assistant discovery disabled. No value will be published to MQTT ! Please check your parameters.")
        return True
      else:
        return True
  
  # Display parameters in log
  def logParams(self):
    
    logging.info("PRONOTE config : username = %s, password = %s", "******@****.**", "******")
    logging.debug("PRONOTE config : username = %s, password = %s, prefixurl = %s", self.pronoteUsername_1, self.pronotePassword_1, self.pronotePrefixUrl_1)
    logging.info("MQTT broker config : host = %s, port = %s, clientId = %s, qos = %s, topic = %s, retain = %s, ssl = %s",
                 self.mqttHost, self.mqttPort, self.mqttClientId,
                 self.mqttQos,self.mqttTopic,self.mqttRetain,
                 self.mqttSsl),
    if self.hassDiscovery:
      logging.info("Home Assistant discovery : Enable = %s, Topic prefix = %s, Device name = %s",
                   self.hassDiscovery, self.hassPrefix, self.hassDeviceName)
    else:
      logging.info("Home Assistant discovery : Enable = %s",self.hassDiscovery)
          
    logging.info("Database options : Force reinitialization = %s, Path = %s", self.dbInit, self.dbPath)
    logging.info("Debug mode : Enable = %s", self.debug)
