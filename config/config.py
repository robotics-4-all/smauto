# Run Mode Setting: Set to "MQTT" to use the Node-RED integration, or to "Local" for a local configuration model.
RUN_MODE = "MQTT"

# Node-RED integration broker settings. Configure this if you have RUN_MODE = "MQTT".
nr_mqtt = {
    "host": "127.0.0.1",
    "username": "my_username",
    "password": "my_password",
    "port": 1883,
    "topic": "ha_auto.model",
}