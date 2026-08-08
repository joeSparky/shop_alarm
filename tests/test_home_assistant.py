from ha.client import HomeAssistantClient


FRONT_DOOR = "binary_sensor.shop_front_door_opening"
ALARM_ARMED = "input_boolean.shop_alarm_armed"
ALARM_TRIGGERED = "input_boolean.shop_alarm_triggered"
TEST_DOOR = "input_boolean.shop_alarm_test_door_open"


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
        ha.call_service("input_boolean", "turn_off", {"entity_id": ALARM_ARMED})
        ha.wait_for_state(ALARM_ARMED, "off", timeout=2)

        try:
            ha.call_service("input_boolean", "turn_on", {"entity_id": ALARM_ARMED})
            ha.wait_for_state(ALARM_ARMED, "on", timeout=2)
            assert ha.state(ALARM_ARMED) == "on"
        finally:
            ha.call_service("input_boolean", "turn_off", {"entity_id": ALARM_ARMED})
            ha.wait_for_state(ALARM_ARMED, "off", timeout=2)

        assert ha.state(ALARM_ARMED) == "off"
        assert ha.state(ALARM_TRIGGERED) == "off"


def test_shop_alarm_virtual_door_triggers_alarm():
    with HomeAssistantClient() as ha:
        # Establish a clean, safe starting state.
        ha.call_service("input_boolean", "turn_off", {"entity_id": TEST_DOOR})
        ha.call_service("input_boolean", "turn_off", {"entity_id": ALARM_ARMED})
        ha.wait_for_state(TEST_DOOR, "off", timeout=2)
        ha.wait_for_state(ALARM_ARMED, "off", timeout=2)
        ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)

        try:
            ha.call_service("input_boolean", "turn_on", {"entity_id": ALARM_ARMED})
            ha.wait_for_state(ALARM_ARMED, "on", timeout=2)

            ha.call_service("input_boolean", "turn_on", {"entity_id": TEST_DOOR})
            ha.wait_for_state(TEST_DOOR, "on", timeout=2)

            ha.wait_for_state(ALARM_TRIGGERED, "on", timeout=2)
            assert ha.state(ALARM_TRIGGERED) == "on"
        finally:
            # Always return Home Assistant to a safe state.
            ha.call_service("input_boolean", "turn_off", {"entity_id": TEST_DOOR})
            ha.call_service("input_boolean", "turn_off", {"entity_id": ALARM_ARMED})
            ha.wait_for_state(TEST_DOOR, "off", timeout=2)
            ha.wait_for_state(ALARM_ARMED, "off", timeout=2)
            ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)
