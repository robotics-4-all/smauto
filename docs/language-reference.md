# SmAuto Language Reference

## Brokers

Brokers define the communication layer. Each entity connects to a broker via a topic. Supported protocols: MQTT, AMQP, Redis.

```
Broker<MQTT> home_broker
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
end
```

```
Broker<AMQP> cloud_broker
    host: "amqp.example.com"
    port: 5672
    ssl: True
    vhost: "/production"
    topicExchange: "amq.topic"
    auth:
        username: "user"
        password: "pass"
end
```

```
Broker<Redis> cache_broker
    host: "redis.example.com"
    port: 6379
    ssl: False
    db: 2
    auth:
        username: ""
        password: "secret"
end
```

| Property | Required | Protocols | Description |
|----------|----------|-----------|-------------|
| `host` | Yes | All | Hostname or IP address |
| `port` | Yes | All | Port number |
| `auth` | Yes | All | Authentication block (`username`, `password`) |
| `ssl` | No | AMQP, Redis | Enable SSL/TLS |
| `vhost` | No | AMQP | Virtual host |
| `topicExchange` | No | AMQP | Topic exchange name |
| `db` | No | Redis | Database number |

## Entities

Entities represent connected devices. Sensors produce data, actuators consume commands, hybrids do both.

```
Entity weather_station
    type: sensor
    freq: 5
    topic: "porch.weather_station"
    broker: home_broker
    attributes:
        - temperature: float
        - humidity: int
        - pressure: float
end

Entity aircondition
    type: actuator
    topic: "bedroom.aircondition"
    broker: home_broker
    attributes:
        - temperature: float
        - mode: str
        - on: bool = false
end
```

| Property | Required | Description |
|----------|----------|-------------|
| `type` | Yes | `sensor`, `actuator`, or `hybrid` |
| `topic` | Yes | Broker topic (use `.` notation, e.g. `bedroom.lamp`) |
| `broker` | Yes | Reference to a defined Broker |
| `attributes` | Yes | List of typed attributes |
| `freq` | No | Publishing frequency in Hz (sensor/hybrid only) |
| `description` | No | Text description |

Each entity references its own broker, enabling multi-broker architectures.

### Attribute Types

| Type | Example | Notes |
|------|---------|-------|
| `int` | `- count: int` | Integer values |
| `float` | `- temperature: float` | Floating point values |
| `bool` | `- active: bool` | `true` / `false` |
| `str` | `- mode: str` | String values |
| `time` | `- timestamp: time` | `HH:MM` format |
| `list` | `- schedule: list` | List / Array |
| `dict` | `- config: dict` | Dictionary |

Default values can be assigned to actuator and hybrid attributes:

```
- power: bool = false
- brightness: int = 0
```

### Built-in Entities

The `system_clock` entity is automatically available in every model. It provides a `time` attribute for time-based conditions:

```
when
    system_clock.time >= 22:00
```

## Value Generators

Sensor and hybrid entities can define value generators and optional noise functions for virtual entity simulation.

```
- temperature: float -> gaussian(10, 20, 5) with noise gaussian(1, 1)
- humidity: float -> linear(1, 0.2) with noise uniform(0, 1)
- pressure: float -> constant(0.5)
```

Syntax: `-> Generator` or `-> Generator with noise Noise`

### Generators

| Generator | Syntax | Description |
|-----------|--------|-------------|
| Constant | `constant(value)` | Fixed value |
| Linear | `linear(start, step)` | Linear increment |
| Saw | `saw(min, max, step)` | Sawtooth wave |
| Sinus | `sinus(value, amplitude, step)` | Sinusoidal wave |
| Gaussian | `gaussian(value, maxValue, sigma)` | Gaussian distribution |
| Replay | `replay([v1, v2, ...], times)` | Replay values (`times=-1` for infinite) |
| ReplayFile | `replayFile("path")` | Replay from file |

### Noise Functions

| Noise | Syntax | Description |
|-------|--------|-------------|
| Uniform | `uniform(min, max)` | Uniform random noise |
| Gaussian | `gaussian(mean, sigma)` | Gaussian random noise |

## Automations

Automations follow an **ECA (Event-Condition-Action)** formalism.

```
Automation start_aircondition
    when
        (weather_station.temperature > 32) AND
        (weather_station.humidity > 60)
    then
        aircondition.temperature <- 25.0
        aircondition.mode <- "cool"
        aircondition.on <- true
    config
        enabled: true
        continuous: false
        description: "Cool down when it gets hot and humid"
end
```

### Structure

| Block | Required | Description |
|-------|----------|-------------|
| `when` | Yes | Condition that triggers the automation |
| `then` | Yes | Actions to execute when condition is met |
| `config` | No | Configuration properties |
| `triggers` | No | Comma-separated list of automations to enable after execution |
| `terminates` | No | Comma-separated list of automations to disable and set to TERMINATED |

### Config Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `enabled` | bool | `true` | Whether the automation evaluates |
| `continuous` | bool | `false` | Keep evaluating after actions execute |
| `checkOnce` | bool | `false` | Evaluate once then stop |
| `freq` | int | — | Evaluation frequency in Hz |
| `delay` | int | — | Delay in seconds before executing actions (debounce) |
| `description` | str | — | Text description |

### Triggers and Terminates

- **`triggers`** — Enables listed automations (sets `enabled = true`) after actions execute successfully.
- **`terminates`** — Disables listed automations and sets their status to `TERMINATED`.

```
Automation start_humidifier
    when
        humidity_sensor.humidity > 0.6
    then
        humidifier.power <- true
    config
        enabled: true
    triggers
        stop_humidifier
end

Automation stop_humidifier
    when
        humidity_sensor.humidity < 0.3
    then
        humidifier.power <- false
    config
        enabled: false
    triggers
        start_humidifier
end
```

### Automation Status Conditions

Automations track their execution status, which can be referenced in conditions to coordinate between automations.

| Status | Meaning |
|--------|---------|
| `IDLE` | Not yet started or waiting to re-evaluate |
| `RUNNING` | Condition is being evaluated |
| `SUCCESS` | Condition met, actions executed successfully |
| `FAILED` | Error during evaluation or action execution |
| `FINISHED` | Actions completed |
| `TERMINATED` | Disabled by another automation via `terminates` |

Use `automation_name.status == STATUS` or `!= STATUS` in `when` blocks:

```
// Status-only condition
Automation start_production
    when
        run_diagnostics.status == SUCCESS
    then
        production_line.running <- true
end

// Mixed: status + entity attribute
Automation charge_battery
    when
        (monitor_solar.status == SUCCESS) AND
        (battery.charge_level < 80)
    then
        inverter.mode <- "charge"
end

// Combined status conditions
Automation recovery_restart
    when
        (handle_failure.status == SUCCESS) AND
        (start_production.status == IDLE)
    then
        control_panel.phase <- "retrying"
end
```

## Conditions

Conditions reference entity attributes using dot notation: `entity_name.attribute_name`.

### Condition Types

**Numeric:**
```
weather_station.temperature > 32
weather_station.temperature == 25.0
```

**String:**
```
aircondition.mode == "cool"
aircondition.mode != "off"
```

**Boolean:**
```
motion_sensor.detected is true
alarm.active is not false
```

**Time:**
```
system_clock.time >= 22:00
system_clock.time < 07:00
```

**Automation Status:**
```
arm_system.status == SUCCESS
calibration.status != FAILED
```

**In-Range:**
```
humidity_sensor.humidity in range [30, 60]
```

### Operators

| Category | Operators |
|----------|-----------|
| Numeric | `>`, `>=`, `<`, `<=`, `==`, `!=` |
| String | `~`, `!~`, `==`, `!=`, `has`, `in`, `not in` |
| Boolean | `is`, `is not` |
| Time | `>`, `>=`, `<`, `<=`, `==`, `!=` |
| Status | `==`, `!=` |
| List / Dict | `==`, `!=` |
| Logical | `AND`, `OR`, `NOT`, `XOR`, `NOR`, `XNOR`, `NAND` |

### Compound Conditions

Combine conditions with logical operators. Each sub-condition must be wrapped in parentheses:

```
(condition_1) AND (condition_2)

((condition_1) AND (condition_2)) OR (condition_3)
```

## Aggregate Functions

Sliding-window aggregate functions can be applied to numeric attributes in conditions:

| Function | Syntax | Description |
|----------|--------|-------------|
| `mean` | `mean(entity.attr, window)` | Mean of last N values |
| `std` | `std(entity.attr, window)` | Standard deviation |
| `var` | `var(entity.attr, window)` | Variance |
| `min` | `min(entity.attr, window)` | Minimum value |
| `max` | `max(entity.attr, window)` | Maximum value |

Functions are composable:

```
when
    var(mean(temp_sensor.temperature, 10), 10) >= 0.1

when
    (mean(grid_meter.consumption, 10) > 500) AND
    (std(vibration_sensor.amplitude, 20) > 1.5)
```

## Actions

Actions assign values to actuator or hybrid entity attributes using the `<-` operator. Listed in the `then` block, one per line.

```
aircondition.temperature <- 25.0
aircondition.mode <- "cool"
aircondition.on <- true
alarm.volume <- 100
lighting.schedule <- [8, 12, 18, 22]
```

Float values require a decimal point (e.g., `25.0` not `25`).

## Metadata

Optional model metadata.

```
Metadata
    name: SmartHome
    version: "0.1.0"
    description: "Home automation model."
    author: "klpanagi"
    email: "klpanagi@gmail.com"
end
```

| Property | Description |
|----------|-------------|
| `name` | Model name |
| `version` | Version string |
| `description` | Model description |
| `author` | Author name |
| `email` | Author email |

## RTMonitor

Configures runtime monitoring for compiled automations.

```
RTMonitor
    broker: home_broker
    namespace: "smauto.home"
    eventTopic: "event"
    logsTopic: "logs"
end
```

| Property | Description |
|----------|-------------|
| `broker` | Reference to a defined Broker |
| `namespace` | URI prefix for runtime topics |
| `eventTopic` | Topic for automation events |
| `logsTopic` | Topic for runtime logs |

## Constraints

The following constraints are enforced at parse time:

- Value generators and noise functions can only be applied to **sensor** and **hybrid** entities
- Actions can only target attributes of **actuator** and **hybrid** entities
- The `freq` property can only be set on **sensor** and **hybrid** entities
- Default attribute values can only be set on **actuator** and **hybrid** entities
- Entity and automation names must be unique within a model
