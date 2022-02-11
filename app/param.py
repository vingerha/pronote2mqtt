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
    
    # Pronote params, note: CAS without quotes
    self.pronoteStudent = 'eveline'
    self.pronoteUsername = 'eveline.vingerhoeds2'
    self.pronotePassword = 'sanyo123'
    self.pronotePrefixUrl = '0061642c'
    self.pronoteEnt = True
    self.pronoteCas = 'atrium_sud'
    
    # Mqtt params
    self.mqttHost = ''
    self.mqttPort = 1883
    self.mqttClientId = 'pronote2mqtt'
    self.mqttUsername = 'iotlink_user'
    self.mqttPassword = ''
    self.mqttQos = 1
    self.mqttTopic = 'pronote'
    self.mqttRetain = True
    self.mqttSsl = False
    
    
    # Run params
    self.scheduleTime = None
    
    # Publication params
    self.standalone = False
    self.hassDiscovery = True
    self.hassPrefix = 'homeassistant'
    self.hassDeviceName = 'pronote'
    self.hassPeriodSensor = True
    self.hassPeriodSensorCount = 10
    
    # Databse params
    self.dbInit = True
    self.dbPath = '.'
    
    # Debug params
    self.debug = True
    
    # Influx db
    self.influxEnable = False
    self.influxHost = None
    self.influxPort = 8086
    self.influxBucket = None
    self.influxOrg = None
    self.influxToken = None
    self.influxHorizon = None

    # Step 2 : Init arguments for command line
    self.args = self.initArg()
    
    # Step 3 : Get params from env variables
    self.getFromOs()
    
    # Step 4 : Get args from command line and overwrite env if needed
    self.getFromArgs()
    
    
  # Set arguments list
  def initArg(self):
    
    self.parser = argparse.ArgumentParser()
    
    self.parser.add_argument(
        "--pronote_username",    help="PRONOTE user name, ex : myemail@email.com")
    self.parser.add_argument(
        "--pronote_password",    help="PRONOTE password")
    self.parser.add_argument(
        "--pronote_prefixurl",    help="PRONOTE prefix url")
    self.parser.add_argument(
        "--pronote_ent",    help="PRONOTE ent")
    self.parser.add_argument(
        "--pronote_cas",    help="PRONOTE case")
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
        "--standalone_mode",  help="Enable standalone publication mode, possible values : True or False")
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
      "--influxdb_enable", help="Enable Influxdb : True or False (default : false)")
    self.parser.add_argument(
      "--influxdb_host", help="Influxdb host")
    self.parser.add_argument(
      "--influxdb_port", help="Influxdb port (default 8086)")
    self.parser.add_argument(
      "--influxdb_org", help="Influxdb organization")
    self.parser.add_argument(
      "--influxdb_bucket", help="Influxdb bucket")
    self.parser.add_argument(
      "--influxdb_token", help="Influxdb token")
    self.parser.add_argument(
      "--influxdb_horizon", help="Influxdb horizon in days ")

    self.parser.add_argument(
        "--debug",            help="Enable debug mode")
    
    return self.parser.parse_args()
  
  
      
  # Load params from Os environment variables 
  def getFromOs(self):
    
    if "PRONOTE_USERNAME" in os.environ: self.pronoteUsername = os.environ["PRONOTE_USERNAME"]
    if "PRONOTE_PASSWORD" in os.environ: self.pronotePassword = os.environ["PRONOTE_PASSWORD"]
    if "PRONOTE_PREFIXURL" in os.environ: self.pronotePrefixUrl = os.environ["PRONOTE_PREFIXURL"]
    if "PRONOTE_ENT" in os.environ: self.pronoteEnt = os.environ["PRONOTE_ENT"]
    if "PRONOTE_CAS" in os.environ: self.pronoteCas = os.environ["PRONOTE_CAS"]
      
    if "MQTT_HOST" in os.environ: self.mqttHost = os.environ["MQTT_HOST"]
    if "MQTT_PORT" in os.environ: self.mqttPort = int(os.environ["MQTT_PORT"])
    if "MQTT_CLIENTID" in os.environ: self.mqttClientId = os.environ["MQTT_CLIENTID"]
    if "MQTT_USERNAME" in os.environ: self.mqttUsername = os.environ["MQTT_USERNAME"]
    if "MQTT_PASSWORD" in os.environ: self.mqttPassword = os.environ["MQTT_PASSWORD"]
    if "MQTT_QOS" in os.environ: self.mqttQos = int(os.environ["MQTT_QOS"])
    if "MQTT_TOPIC" in os.environ: self.mqttTopic = os.environ["MQTT_TOPIC"]
    if "MQTT_RETAIN" in os.environ: self.mqttRetain = _isItTrue(os.environ["MQTT_RETAIN"])
    if "MQTT_SSL" in os.environ: self.mqttSsl = _isItTrue(os.environ["MQTT_SSL"])
      
    if "SCHEDULE_TIME" in os.environ: self.scheduleTime = os.environ["SCHEDULE_TIME"]
      
    if "STANDALONE_MODE" in os.environ: self.standalone = _isItTrue(os.environ["STANDALONE_MODE"])
    if "HASS_DISCOVERY" in os.environ: self.hassDiscovery = _isItTrue(os.environ["HASS_DISCOVERY"])
    if "HASS_PREFIX" in os.environ: self.hassPrefix = os.environ["HASS_PREFIX"]
    if "HASS_DEVICE_NAME" in os.environ: self.hassDeviceName = os.environ["HASS_DEVICE_NAME"]
        
    if "DB_INIT" in os.environ: self.dbInit = _isItTrue(os.environ["DB_INIT"])
    if "DB_PATH" in os.environ: self.dbPath = os.environ["DB_PATH"]

    if "INFLUXDB_ENABLE" in os.environ: self.influxEnable = _isItTrue(os.environ["INFLUXDB_ENABLE"])
    if "INFLUXDB_HOST" in os.environ: self.influxHost = os.environ["INFLUXDB_HOST"]
    if "INFLUXDB_PORT" in os.environ: self.influxPort = int(os.environ["INFLUXDB_PORT"])
    if "INFLUXDB_ORG" in os.environ: self.influxOrg = os.environ["INFLUXDB_ORG"]
    if "INFLUXDB_BUCKET" in os.environ: self.influxBucket = os.environ["INFLUXDB_BUCKET"]
    if "INFLUXDB_TOKEN" in os.environ: self.influxToken = os.environ["INFLUXDB_TOKEN"]
    if "INFLUXDB_HORIZON" in os.environ: self.influxHorizon = os.environ["INFLUXDB_HORIZON"]
  
    if "DEBUG" in os.environ: self.debug = _isItTrue(os.environ["DEBUG"])
  
  
  # Get params from arguments in command line
  def getFromArgs(self):
    
    if self.args.pronote_username is not None: self.pronoteUsername = self.args.pronote_username
    if self.args.pronote_password is not None: self.pronotePassword = self.args.pronote_password
    if self.args.pronote_prefixurl is not None: self.pronotePrefixUrl = self.args.pronote_prefixurl
    if self.args.pronote_ent is not None: self.pronoteEnt = self.args.pronote_end
    if self.args.pronote_cas is not None: self.pronotePassword = self.args.pronote_cas
      
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
      
    if self.args.standalone_mode is not None: self.standalone = _isItTrue(self.args.standalone_mode)
    if self.args.hass_discovery is not None: self.hassDiscovery = _isItTrue(self.args.hass_discovery)
    if self.args.hass_prefix is not None: self.hassPrefix = self.args.hass_prefix
    if self.args.hass_device_name is not None: self.hassDeviceName = self.args.hass_device_name
            
    if self.args.db_init is not None: self.dbInit = _isItTrue(self.args.db_init)
    if self.args.db_path is not None: self.db_path = self.args.db_path

    if self.args.influxdb_enable is not None: self.influxEnable = _isItTrue(self.args.influxdb_enable)
    if self.args.influxdb_host is not None: self.influxHost = self.args.influxdb_host
    if self.args.influxdb_port is not None: self.influxPort = int(self.args.influxdb_port)
    if self.args.influxdb_org is not None: self.influxOrg = self.args.influxdb_org
    if self.args.influxdb_bucket is not None: self.influxBucket = self.args.influxdb_bucket
    if self.args.influxdb_token is not None: self.influxToken = self.args.influxdb_token
    if self.args.influxdb_horizon is not None: self.influxHorizon = self.args.influxdb_horizon
      
    if self.args.debug is not None: self.debug = _isItTrue(self.args.debug)
    
    
  # Check parameters
  def checkParams(self):
    
    if self.pronoteUsername is None:
      logging.error("Parameter PRONOTE username is mandatory.")
      return False
    elif self.pronotePassword is None:
      logging.error("Parameter PRONOTE password is mandatory.")
      return False
    elif self.pronotePrefixUrl is None:
      logging.error("Parameter PRONOTE prefixurl is mandatory.")
      return False
    elif self.mqttHost is None:
      logging.error("Parameter MQTT host is mandatory.")
      return False
    else:
      if self.standalone == False and self.hassDiscovery == False:
        logging.warning("Both Standalone mode and Home assistant discovery are disable. No value will be published to MQTT ! Please check your parameters.")
        return True
      elif self.influxEnable:
        if self.influxHost == None or self.influxOrg == None or self.influxBucket == None or self.influxToken == None:
          logging.error("At least one parameters of Influxdb is missing (host, org, bucket or token)")
          return False
        else:
          return True
      else:
        return True
  
  # Display parameters in log
  def logParams(self):
    
    logging.info("PRONOTE config : username = %s, password = %s", "******@****.**", "******")
    logging.debug("PRONOTE config : username = %s, password = %s, prefixurl = %s", self.pronoteUsername, self.pronotePassword, self.pronotePrefixUrl)
    logging.info("MQTT broker config : host = %s, port = %s, clientId = %s, qos = %s, topic = %s, retain = %s, ssl = %s",
                 self.mqttHost, self.mqttPort, self.mqttClientId,
                 self.mqttQos,self.mqttTopic,self.mqttRetain,
                 self.mqttSsl),
    logging.info("Standalone mode : Enable = %s", self.standalone)
    if self.hassDiscovery:
      logging.info("Home Assistant discovery : Enable = %s, Topic prefix = %s, Device name = %s",
                   self.hassDiscovery, self.hassPrefix, self.hassDeviceName)
    else:
      logging.info("Home Assistant discovery : Enable = %s",self.hassDiscovery)
    
    if self.influxEnable:
      logging.info("Influxdb config : Enable = %s, Host = %s, Port = %s, Org = %s, Bucket = %s, Token = ***",
                   self.influxEnable, self.influxHost, self.influxPort, self.influxOrg, self.influxBucket)
    else:
      logging.info("Influxdb config : Enable = %s",self.influxEnable)
      
    logging.info("Database options : Force reinitialization = %s, Path = %s", self.dbInit, self.dbPath)
    logging.info("Debug mode : Enable = %s", self.debug)

