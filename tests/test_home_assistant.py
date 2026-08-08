from ha.client import HomeAssistantClient


FRONT_DOOR = "binary_sensor.shop_front_door_opening"
ALARM_MODE = "input_select.shop_alarm_mode"
ALARM_TRIGGERED = "input_boolean.shop_alarm_triggered"
TEST_DOOR = "input_boolean.shop_alarm_test_door_open"


def set_mode(ha: HomeAssistantClient, mode: str) -> None:
    ha.call_service(
        "input_select",
        "select_option",
        {"entity_id": ALARM_MODE, "option": mode},
    )
    ha.wait_for_state(ALARM_MODE, mode, timeout=2)


def close_test_door(ha: HomeAssistantClient) -> None:
    ha.call_service("input_boolean", "turn_off", {"entity_id": TEST_DOOR})
    ha.wait_for_state(TEST_DOOR, "off", timeout=2)


def open_test_door(ha: HomeAssistantClient) -> None:
    ha.call_service("input_boolean", "turn_on", {"entity_id": TEST_DOOR})
    ha.wait_for_state(TEST_DOOR, "on", timeout=2)


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


def test_shop_alarm_mode_entity_exists():
    with HomeAssistantClient() as ha:
        assert ha.state(ALARM_MODE) in ("Disarmed", "Home", "Away", "Sleep")


def test_shop_alarm_triggered_entity_exists():
    with HomeAssistantClient() as ha:
        assert ha.state(ALARM_TRIGGERED) in ("on", "off")


def test_shop_alarm_can_select_all_modes():
    with HomeAssistantClient() as ha:
        try:
            for mode in ("Home", "Away", "Sleep", "Disarmed"):
                set_mode(ha, mode)
                assert ha.state(ALARM_MODE) == mode
        finally:
            set_mode(ha, "Disarmed")


def test_home_mode_ignores_virtual_door():
    with HomeAssistantClient() as ha:
        set_mode(ha, "Disarmed")
        close_test_door(ha)
        ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)

        try:
            set_mode(ha, "Home")
            open_test_door(ha)
            assert ha.state(ALARM_TRIGGERED) == "off"
        finally:
            close_test_door(ha)
            set_mode(ha, "Disarmed")
            ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)


def test_away_mode_virtual_door_triggers_alarm():
    with HomeAssistantClient() as ha:
        set_mode(ha, "Disarmed")
        close_test_door(ha)
        ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)

        try:
            set_mode(ha, "Away")
            open_test_door(ha)
            ha.wait_for_state(ALARM_TRIGGERED, "on", timeout=2)
            assert ha.state(ALARM_TRIGGERED) == "on"
        finally:
            close_test_door(ha)
            set_mode(ha, "Disarmed")
            ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)


def test_sleep_mode_virtual_door_triggers_alarm():
    with HomeAssistantClient() as ha:
        set_mode(ha, "Disarmed")
        close_test_door(ha)
        ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)

        try:
            set_mode(ha, "Sleep")
            open_test_door(ha)
            ha.wait_for_state(ALARM_TRIGGERED, "on", timeout=2)
            assert ha.state(ALARM_TRIGGERED) == "on"
        finally:
            close_test_door(ha)
            set_mode(ha, "Disarmed")
            ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)
