from ha.client import HomeAssistantClient


FRONT_DOOR = "binary_sensor.shop_front_door_opening"
ALARM_ARMED = "input_boolean.shop_alarm_armed"
ALARM_TRIGGERED = "input_boolean.shop_alarm_triggered"


def test_home_assistant_api_is_running():
    with HomeAssistantClient() as ha:
        assert ha.api_status() == "API running."


def test_front_door_sensor_exists():
    with HomeAssistantClient() as ha:
        assert ha.state(FRONT_DOOR) in ("on", "off")


def test_wait_for_front_door_current_state():
    with HomeAssistantClient() as ha:
        current_state = ha.state(FRONT_DOOR)
        result = ha.wait_for_state(FRONT_DOOR, current_state, timeout=2)
        assert result["state"] == current_state


def test_shop_alarm_armed_entity_exists():
    with HomeAssistantClient() as ha:
        assert ha.state(ALARM_ARMED) in ("on", "off")


def test_shop_alarm_triggered_entity_exists():
    with HomeAssistantClient() as ha:
        assert ha.state(ALARM_TRIGGERED) in ("on", "off")
