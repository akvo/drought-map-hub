#!/bin/bash

# Load .env from ./geonode
GEOSERVER_PUBLIC_LOCATION=$(grep GEOSERVER_PUBLIC_LOCATION= ./geonode/.env | cut -d '=' -f2)
ADMIN_USER=$(grep GEOSERVER_ADMIN_USER= ./geonode/.env | cut -d '=' -f2)
ADMIN_PASSWORD=$(grep GEOSERVER_ADMIN_PASSWORD= ./geonode/.env | cut -d '=' -f2)

echo "Updating GeoServer admin password..."
response=$(curl -s -k -w "%{http_code}" -u "${ADMIN_USER}:geoserver" \
    -X PUT \
    -H "Content-Type: application/json" \
    -d "{ \"newPassword\": \"${ADMIN_PASSWORD}\" }" \
    "${GEOSERVER_PUBLIC_LOCATION}/rest/security/self/password")

http_status="${response: -3}"
if [ "$http_status" -eq 200 ]; then
    echo "Password updated successfully, waiting 15 seconds for GeoServer to process the password change..."
    sleep 15
fi

# Try to update the XML external entities setting
echo "Setting xmlExternalEntitiesEnabled to true in GeoServer..."
curl -s -k -u "${ADMIN_USER}:${ADMIN_PASSWORD}" \
    -X PUT \
    -H "Content-Type: application/xml" \
    -d '<global>
    <xmlExternalEntitiesEnabled>true</xmlExternalEntitiesEnabled>
    </global>' \
    "${GEOSERVER_PUBLIC_LOCATION}/rest/settings.xml"

echo "Post-installation script completed."