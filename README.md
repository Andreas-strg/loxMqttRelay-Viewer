# loxMqttRelay Viewer Beta

![example](\\DiskStation\docker\loxmqttrelayviewer\foto.png)

### Docker Compose example

```yaml
services:
  loxmqtteelayviewer:
    container_name: loxMqttRelayViewer
    build: https://github.com/Andreas-strg/loxMqttRelay-Viewer.git
    ports:
      - 8000:8000
    environment:
      - MQTT_BROKER=
      - MQTT_PORT=1883
      - MQTT_USERNAME=
      - MQTT_PASSWORD=
      - WEB_PASSWORD= #not needed
```
