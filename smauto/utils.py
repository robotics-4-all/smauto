import os

from textx import get_children_of_type


def select_clock_broker(model):
    """Select the first non-fake broker from the model for the system clock."""
    brokers = []
    for m in model._tx_model_repository.all_models:
        brokers += get_children_of_type("MQTTBroker", m)
        brokers += get_children_of_type("AMQPBroker", m)
        brokers += get_children_of_type("RedisBroker", m)
    for broker in brokers:
        if broker.name == "fake_broker":
            brokers.remove(broker)
    return brokers[0]


def make_executable(path):
    """Set executable permission on a file by copying read bits to execute bits."""
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2  # copy R bits to X
    os.chmod(path, mode)


def inject_system_clock(model):
    """Inject the built-in system_clock entity into the model, swapping its source to the first real broker."""
    clock_broker = select_clock_broker(model)
    for m in model._tx_model_repository.all_models:
        if m.metadata and m.metadata.name == "SystemClock":
            m.entities[0].source = clock_broker
            ent = m.entities[0]
            if ent not in model.entities:
                model.entities.append(ent)
            model.system_clock = ent
            return ent
    return None
