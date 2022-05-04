#!/bin/sh
set -e

if [ ! -z "$PRONOTE2MQTT_APP" ]; then
    APP="$PRONOTE2MQTT_APP"
else
    APP="/app"
fi

echo "Using '$APP' as APP directory"

if [ ! -f "$APP/param.py" ]; then
    echo "Param.py non existing, copying default to app..."
    cp /app_temp/param.py "$APP/param.py"
fi
if [ ! -f "$APP/pronote.py" ]; then
    echo "pronote.py non existing, copying default to app..."
    cp /app_temp/pronote.py "$APP/pronote.py"
fi
if [ ! -f "$APP/pronote2mqtt.py" ]; then
    echo "pronote2mqtt.py non existing, copying default to app..."
    cp /app_temp/pronote2mqtt.py "$APP/pronote2mqtt.py"
fi
if [ ! -f "$APP/database.py" ]; then
    echo "pronote2mqtt.py non existing, copying default to app..."
    cp /app_temp/database.py "$APP/database.py"
fi
if [ ! -f "$APP/mqtt.py" ]; then
    echo "mqtt.py non existing, copying default to app..."
    cp /app_temp/mqtt.py "$APP/mqtt.py"
fi
if [ ! -f "$APP/database.py" ]; then
    echo "hass.py non existing, copying default to app..."
    cp /app_temp/hass.py "$APP/hass.py"
fi

exec "$@"
