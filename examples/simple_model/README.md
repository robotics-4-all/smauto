---

Simple example for beginners. In this example, in which the air conditioner is turned on according to the temperature and humidity.

```yaml
mqtt:
    name: home_broker
    host: "localhost"
    port: 1883
    credentials:
        username: "username"
        password: "password"

entity:
    name: weather_station
    topic: "porch.weather_station"
    broker: home_broker
    attributes:
        - temperature: float
        - humidity: int

entity:
    name: aircondition
    topic: "bedroom.aircondition"
    broker: home_broker
    attributes:
        - temperature: float
        - mode: string
        - on: bool

automation:
    name: start_aircondition
    condition: ((weather_station.temperature > 32) AND (weather_station.humidity > 30)) AND (aircondition.on NOT true)
    enabled: true
    continuous: false
    actions:
        - aircondition.temperature:  25.0
        - aircondition.mode:  "cool"
        - aircondition.on:  true
```

If you do not already have installed [smauto-cli](), please head to the main page of
this repo and follow the [installation instructions](https://github.com/robotics-4-all/smauto-dsl#installation).

To execute the model, simply call the interpreter.

```bash
smauto interpret simple_model.smauto
```

```bash
[*] Executing automation <start_aircondition>...
[*] Condition: (((model.entities_dict['weather_station'].attributes_dict['temperature'].value > 32) and (model.entities_dict['weather_station'].attributes_dict['humidity'].value > 30)) and (model.entities_dict['aircondition'].attributes_dict['on'].value is not True))
```

To test the automation use [commlib-cli](https://github.com/robotics-4-all/commlib-cli) to create a dummy `weather_station`.

```bash
commlib-cli --btype mqtt pub 'porch/weather_station' '{"temperature": 33, "humidity": 31}'
```

You should see at the console reporting completion of the automation.

```bash
[*] Automation <start_aircondition> Triggered!
[*] All automations completed!!
```
