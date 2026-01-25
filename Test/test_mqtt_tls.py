import ssl
import time
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 8883
TOPIC = "test"

# CA-Zertifikat explizit angeben
CA_FILE = r"C:\mosquitto\certs\ca.crt"

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Verbunden mit Broker")
        client.subscribe(TOPIC)
    else:
        print("❌ Verbindungsfehler:", rc)

def on_message(client, userdata, msg):
    print(f"📩 Nachricht empfangen: {msg.payload.decode()}")

# Neue API-Version benutzen
client = mqtt.Client(client_id="", protocol=mqtt.MQTTv311)

# TLS aktivieren mit deiner CA
client.tls_set(
    ca_certs=CA_FILE,  # <--- hier deine selbstsignierte CA
    certfile=None,
    keyfile=None,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)

# self-signed Zertifikate nicht unsicher setzen
client.tls_insecure_set(False)

client.on_connect = on_connect
client.on_message = on_message

print("🔄 Verbinde...")

client.connect(BROKER, PORT, keepalive=60)

client.loop_start()
time.sleep(2)

# Testnachricht senden
client.publish(TOPIC, "Hallo über TLS 🚀")

time.sleep(5)
client.loop_stop()
client.disconnect()
print("👋 Verbindung getrennt")