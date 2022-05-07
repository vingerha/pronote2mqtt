<h2 align="center">MQTT integration for HomeAssistant using data from pronotepy.</h2>
<h3 align="center" color="red">Initial release, finetuning ongoing</h3>


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


##Installation
### Releases
**Initial version**

1. Install directly from docker : `docker pull vingerha/pronote2mqtt:latest`
It is recommended to map the volumes 'app' and 'data' so one can access these easier. 
The docker entryscsript will ensure that the files are copied into that volumne and will (should) not overrride existin param.py or ent.py as these are used for local config. In exceptional cases, the python files must be manually copied into the 'app' folder (please send me any use-case as 'issue')
The 'data' folder will contain the sqlite3 database: pronote2mqtt.db, then you can access its data with e.g. 'DB Browser for SQLite'.
2. Update the params.py with your values to connect to MQTT and pronote.
3. Update ent.py. I have added an ent.py based on the one by pronotepy. The package currently assumes that you are accessing over CAS (as do most students), so make sure that ent.py has your specific CAS properly setup...for details check pronotepy on how to update your CAS in ent.py.

**0.3.0**
Integrated with pronotepy 2.4.0 as this contains more CAS now, removed 'proprietary' ent.py
Added pycron to be able the schedule the runs with more details, see param.py (removed all other scheduling options)

**v0.4.0**
Fixed issue when pronote is presenting multiple lessons for the same slot (e.g. canceled => changed or changed => cancelled), solution is via highest 'num'
Note that in order to make this work, the database needs to be reïnitialised as a new column was added (lessonNum)

**latest**
Initial attempts to add the option to extract data as 'parent' and not 'eleve'
Fixed 'averages' as not longer provided for 'Année continue', towards MQTT it publishes only the last period (Trimestre)

#### Testing the package
To self test pronote2mqtt, run the docker container: `docker run --name pronote2mqtt_test --tty vingerha/pronote2mqtt:latest`.
After the run, in the container you will find a pronote2mqtt.db in /data (which is also a parmetered value)

Or from commandline, in the folder where you stored the files form /app, using this command:
`python3 pronote2mqtt`

*Please keep in mind that the deault param.py settings have a demo-user only, so you need to add upir username/pwd/ent/cas in param.py*

#### Upgradeing
When (re)starting the container, it verifies if the app folder contains the correct files. If not, then it will copy them from the source.
If you have downloaded a new image and created a new container, one should remove all files EXCEPT param.py...this way your new version has a chance on starting without any additional updates.

### Long Term Usage

Pronote2mqtt will try and reconnect at fixed times (param.py default: 06:00). It depends on pronotepy so cannot assure that it will continue to be working. 

## Contributing

Feel free to contribute anything. Any help is appreciated. To contribute, please create a pull request with your changes.

## Adding content

Most parts are covered but if you need anything that is not yet implemented, you can [create an issue] (https://github.com/vingerha/pronote2mqtt/issues/new) with your request. (or you can contribute by adding it yourself)

## License

Copyright (c) 2022 vingerha

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
