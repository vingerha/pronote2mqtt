#!/bin/sh
set -e

if [ ! -z "$PRONOTE2MQTT_APP" ]; then
    APP="$PRONOTE2MQTT_APP"
else
    APP="/app"
fi

echo "Using '$APP' as APP directory"

echo "Copying files to app..."
cp -r /app_temp/* "$APP"

exec "$@"
