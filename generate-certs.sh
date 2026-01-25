#!/bin/bash
# Generate TLS certificates for Mosquitto

CERT_DIR="./mosquitto/config/certs"
mkdir -p $CERT_DIR
cd $CERT_DIR

# Generate private key
openssl genrsa -out mosquitto.key 2048

# Generate self-signed certificate valid for 10 years
openssl req -new -x509 -key mosquitto.key -out mosquitto.crt -days 3650 \
  -subj "/C=DE/ST=Berlin/L=Berlin/O=SmartCar/CN=mosquitto"

# Generate CA cert (copy from key for self-signed)
cp mosquitto.crt ca.crt

echo "TLS Certificates generated successfully!"
ls -la $CERT_DIR
