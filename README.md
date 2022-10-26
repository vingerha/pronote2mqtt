<h2 align="center">MQTT integration for HomeAssistant using data from pronotepy.</h2>
<h3 align="center" color="red">Finetuning ongoing</h3>


<h3 align="center">--------------------------------------------------------</h3>


## Introduction
This is a Python wrapper on top of pronotepy. Every function was tested assuming a family with two students (eleves). 
The package is provided as a docker image which also installs pronotepy as part of it. 
One can choose to separately install pronotepy (see: github bainf3/pronotepy) and separately use the files in 'app', making sure that elements as specified in '/app/requirements.txt' are installed too.

The integration will create a device per student/user and sensors for 
- Student
- Grade
- Average
- Absence
- Homework
- Evaluation (Note: Evaluation is replacing Grade over time, i.e. 'mentions' instead of grade-values)

Note for below, you need to install the card-mod from hacs
The sensors can be made visible in Home Assistant using the markdown-card, an example is included. (https://github.com/vingerha/pronote2mqtt/blob/main/example_markdown.yaml)
![image](https://user-images.githubusercontent.com/44190435/154719453-895ee43e-2f27-41e5-8000-76c346ca0579.png)
In HA automations, one can add a notification that will send a app-message if updated, this example show last 2 evaluations: (https://github.com/vingerha/pronote2mqtt/blob/main/example_notification.yaml)


## About

### Disclaimer
As many others on github, I am creating/maintaining this software in my spare time. 
With any new update/version, I do not (!) verify if this is backwards compatible and the database may need to be reset, leading to possible data-losses.

- Advise 1: at-least make a backup of your database and app folder before loading new image and starting the container
- Advise 2: run a new separate container on the latest image and test it out, before deciding to use it in full...e.g. create a pronote2mqtt_update

### Dependencies

1. pronotepy: this is the actual software that extracts the data from pronote (https://github.com/bain3/pronotepy). The docker image includes this packages and any information on the version is noted in my release notes below
2. MQTT as a broker, you need to install this yourselves


#### Releases

**latest**
Note: 'latest' will see updates as and when I see fit wihtout much communication (other then below) and I am not guaranteeing it to work. 

**0.5.0**
- integrated pronotepy 2.7.0
- merged two pull requests to align parameters and split out grade / out of
- updated datbase tables evaluations: 'null' field seen as unique in SQLite and added few new fields
- updated datbase tables lessons, lessonStatus
- at the start of the run, lessons are deleted for thos today+future, this as lesson records can not be identified as valid wrt to lessons loaded in the past. Too many variations exist. IMO this is not an issue as it concerns today and future so always up to date with pronite after each run
- NOT fixed: issue with agora06 as still awaiting pronotepy to embed this


**v0.4.1**
- Added option to extract data as 'parent' and not 'eleve', includes a solution for having two kids on the same school.
- Fixed 'averages' as not longer provided for 'Année continue', towards MQTT it publishes only the last period (Trimestre)

**v0.4.0**
- Fixed issue when pronote is presenting multiple lessons for the same slot (e.g. canceled => changed or changed => cancelled), solution is via highest 'num'
- Note that in order to make this work, the database needs to be reïnitialised as a new column was added (lessonNum)

**0.3.0**
- Integrated with pronotepy 2.4.0 as this contains more CAS now, removed 'proprietary' ent.py
- Added pycron to be able the schedule the runs with more details, see param.py (removed all other scheduling options)

## Installation

### Base install

1. Install directly from docker : `docker pull vingerha/pronote2mqtt:latest`
It is recommended to map the volumes 'app' and 'data' so one can access these easier...if docker already has write access then it will create thse folders itself.
Example: 'docker run --name pronote2mqtt -v /home/docker/pronote2mqtt/app:/app -v /home/docker/pronote2mqtt:/data --tty vingerha/pronote2mqtt:latest'
The docker entryscsript will ensure that the files are copied into that volume and will (should) not overrride existin param.py or ent.py as these are used for local config. In exceptional cases, the python files must be manually copied into the 'app' folder (please send me any use-case as 'issue')
The 'data' folder will contain the sqlite3 database: pronote2mqtt.db, then you can access its data with e.g. 'DB Browser for SQLite'.
2. Update the params.py with your values to connect to MQTT and pronote.
3. Update ent.py. I have added an ent.py based on the one by pronotepy. The package currently assumes that you are accessing over CAS (as do most students), so make sure that ent.py has your specific CAS properly setup...for details check pronotepy on how to update your CAS in ent.py.

### Testing the package
To self test pronote2mqtt, run the docker container: `docker run --name pronote2mqtt_test --tty vingerha/pronote2mqtt:latest`.
After the run, in the container you will find a pronote2mqtt.db in /data (which is also a parmetered value)

Or from commandline, in the folder where you stored the files form /app, using this command:
`python3 pronote2mqtt`

*Please keep in mind that the deault param.py settings have a demo-user only, so you need to add upir username/pwd/ent/cas in param.py*

### Upgrade
When (re)starting the container, it verifies if the app folder contains the correct files. If not, then it will copy them from the source.
If you have downloaded a new image and created a new container, one should remove all files EXCEPT param.py...this way your new version has a chance on starting without any additional updates.

### param.py ('latest' version)
Explanations with the various params

    self.pronoteUsername_1 : username to get access to pronote, use quotes
    self.pronotePassword_1 : related password, use quotes
    self.pronotePrefixUrl_1 : pre-fix url to the pronote url, you should have received this from your school,  https://'prefix_url'.index-education.net/pronote/eleve.html
    self.pronoteEnt_1 : if your access requires a ENT to grant access, True or False
    self.pronoteCas_1 : the ent/cas that you are part of, use quotes 
    self.pronoteGradesAverages_1 : collect grades and averages for this access, 'new' form collèges no longer use this, they have 'Evaluations' (color scheme), True or False
    
    self.pronoteParent_1 : if you are using a parent access instead of eleve, i.e. https://'+prefix_url+'.index-education.net/pronote/parent.html, True or False
    self.pronoteFullName_1 : if you are using parent access and (!) have more children add child name in the form "NAME Firstname"
    
	.. for the second section with '_2', same as above but when having a second child or when using parent with 2 children in the same school
	
	At the moment it does not support more that 2 children, if you require more than 2, then the workaround is to add a secondary container allowing you to add two more
 
    
    # Mqtt params, note: I have not setup or tested SSL connection and for the moment not supporting that
    self.mqttHost = '' : enter ipaddress
    self.mqttPort = 1883 : change only if you changed the default mqtt port
    self.mqttClientId = 'pronote2mqtt' : change at your convenience
    self.mqttUsername = '' : add if needed
    self.mqttPassword = '' : add if needed
    self.mqttQos = 1 : change at your convenience
    self.mqttTopic = 'pronote' : change at your convenience
    self.mqttRetain = True : change at your convenience
    self.mqttSsl = False : change at your convenience
    
   
    # cron (used in pronotepy2mqtt) in order: on minute 0 (so every full hour) / on hours 6 till 20 / every day in month / every month on weekdays sunday till friday
    self.scheduleCron = '0 6-20 * * sun-fri' 
    
    # Publication params
    self.hassDiscovery = True : to publish it for HA discovery
    self.hassPrefix = 'homeassistant' : the topic section in which it occurs
    self.hassDeviceName = 'pronote' : prefix to identify them
    self.hassPeriodSensor = True : adds periods as a sensor too, most installs donot need this
    self.hassPeriodSensorCount = 10 : how many periods are shown, most installs donot need this
    
    # Database params
    self.dbInit = True : resets the database from scratch each and every run. Set to False if you want to accumulate data
    self.dbPath = './data' : folder in which the database is stored, leave as-is unless you have a good reason to store elsewhere
    
    # Debug params
    self.debug = False : when set to True it will send (a lot) of log messages, only use in case of issues 
    
    # Step 2 : Init arguments for command line
    self.args = self.initArg() : donot change unless you know what you are doing
     
    # Step 3 : Get args from command line and overwrite env if needed
    self.getFromArgs() : donot change unless you know what you are doing


### Scheduled runs

Pronote2mqtt will try and reconnect at fixed times as per param.py where ootb it is to sun-fri between 6 and 20, using a cron-alike setup (pycron). 

## Contributing and/or enhancement requests

Feel free to contribute anything. Any help is appreciated. To contribute, please create a pull request with your changes.
Most parts are covered to my personal needs, but if you need anything that is not yet implemented, you can [create an issue] (https://github.com/vingerha/pronote2mqtt/issues/new) with your request. (or you can contribute by adding it yourself)

## License

Copyright (c) 2022 vingerha

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
