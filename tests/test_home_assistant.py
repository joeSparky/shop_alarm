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


def test_shop_alarm_can_arm_and_disarm():
    with HomeAssistantClient() as ha:
        # Start from a known, safe state.
        ha.call_service("input_boolean", "turn_off", {"entity_id": ALARM_ARMED})
        ha.wait_for_state(ALARM_ARMED, "off", timeout=2)

        try:
            ha.call_service("input_boolean", "turn_on", {"entity_id": ALARM_ARMED})
            ha.wait_for_state(ALARM_ARMED, "on", timeout=2)
            assert ha.state(ALARM_ARMED) == "on"
        finally:
            # Always leave the shop alarm disarmed, even if an assertion fails.
            ha.call_service("input_boolean", "turn_off", {"entity_id": ALARM_ARMED})
            ha.wait_for_state(ALARM_ARMED, "off", timeout=2)

        assert ha.state(ALARM_ARMED) == "off"
        assert ha.state(ALARM_TRIGGERED) == "off"
