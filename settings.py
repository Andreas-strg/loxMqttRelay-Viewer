# 📡 MQTT Einstellungen
MQTT_BROKER = os.getenv("MQTT_BROKER", "192.168.178.25")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "andreas")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "qu!ckMetal90")