from ha.client import HomeAssistantClient


FRONT_DOOR = "binary_sensor.shop_front_door_opening"
ALARM_MODE = "input_select.shop_alarm_mode"
ALARM_STATE = "input_select.shop_alarm_state"
ALARM_TRIGGERED = "input_boolean.shop_alarm_triggered"
TEST_DOOR = "input_boolean.shop_alarm_test_door_open"
TEST_MODE = "input_boolean.shop_alarm_test_mode"
NOTIFY_ACTION = "input_text.shop_alarm_notify_action"


def set_mode(ha: HomeAssistantClient, mode: str) -> None:
    ha.call_service(
        "input_select",
        "select_option",
        {"entity_id": ALARM_MODE, "option": mode},
    )
    ha.wait_for_state(ALARM_MODE, mode, timeout=2)


def set_boolean(ha: HomeAssistantClient, entity_id: str, on: bool) -> None:
    service = "turn_on" if on else "turn_off"
    target_state = "on" if on else "off"
    ha.call_service("input_boolean", service, {"entity_id": entity_id})
    ha.wait_for_state(entity_id, target_state, timeout=2)


def close_test_door(ha: HomeAssistantClient) -> None:
    set_boolean(ha, TEST_DOOR, False)


def open_test_door(ha: HomeAssistantClient) -> None:
    set_boolean(ha, TEST_DOOR, True)


def reset_alarm(ha: HomeAssistantClient) -> None:
    close_test_door(ha)
    set_mode(ha, "Disarmed")
    ha.wait_for_state(ALARM_STATE, "Disarmed", timeout=2)
    ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)


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


def test_shop_alarm_state_entity_exists():
    with HomeAssistantClient() as ha:
        assert ha.state(ALARM_STATE) in (
            "Disarmed",
            "Armed Home",
            "Exit Delay",
            "Armed Away",
            "Armed Sleep",
            "Entry Delay",
            "Alarm",
        )


def test_shop_alarm_triggered_entity_exists():
    with HomeAssistantClient() as ha:
        assert ha.state(ALARM_TRIGGERED) in ("on", "off")


def test_shop_alarm_notify_action_entity_exists():
    with HomeAssistantClient() as ha:
        assert isinstance(ha.state(NOTIFY_ACTION), str)


def test_mobile_app_notify_action_is_configured():
    with HomeAssistantClient() as ha:
        candidates = ha.service_names("notify", prefix="mobile_app_")
        assert len(candidates) == 1, (
            "Expected exactly one Home Assistant mobile-app notify action; "
            f"found {candidates!r}."
        )
        action = f"notify.{candidates[0]}"
        ha.call_service(
            "input_text",
            "set_value",
            {"entity_id": NOTIFY_ACTION, "value": action},
        )
        ha.wait_for_state(NOTIFY_ACTION, action, timeout=2)
        assert ha.state(NOTIFY_ACTION) == action


def test_shop_alarm_can_select_all_modes():
    with HomeAssistantClient() as ha:
        set_boolean(ha, TEST_MODE, True)
        try:
            for mode in ("Home", "Away", "Sleep", "Disarmed"):
                set_mode(ha, mode)
                assert ha.state(ALARM_MODE) == mode
        finally:
            set_mode(ha, "Disarmed")
            set_boolean(ha, TEST_MODE, False)


def test_home_mode_ignores_virtual_door():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        try:
            set_mode(ha, "Home")
            ha.wait_for_state(ALARM_STATE, "Armed Home", timeout=2)
            open_test_door(ha)
            assert ha.state(ALARM_TRIGGERED) == "off"
            assert ha.state(ALARM_STATE) == "Armed Home"
        finally:
            reset_alarm(ha)


def test_away_mode_has_exit_delay_then_arms():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            set_mode(ha, "Away")
            ha.wait_for_state(ALARM_STATE, "Exit Delay", timeout=2)
            ha.wait_for_state(ALARM_STATE, "Armed Away", timeout=3)
            assert ha.state(ALARM_TRIGGERED) == "off"
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


def test_away_mode_virtual_door_runs_entry_delay_then_alarm():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            set_mode(ha, "Away")
            ha.wait_for_state(ALARM_STATE, "Armed Away", timeout=3)
            open_test_door(ha)
            ha.wait_for_state(ALARM_STATE, "Entry Delay", timeout=2)
            ha.wait_for_state(ALARM_STATE, "Alarm", timeout=3)
            assert ha.state(ALARM_TRIGGERED) == "on"
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


def test_disarm_during_entry_delay_prevents_alarm():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            set_mode(ha, "Sleep")
            ha.wait_for_state(ALARM_STATE, "Armed Sleep", timeout=2)
            open_test_door(ha)
            ha.wait_for_state(ALARM_STATE, "Entry Delay", timeout=2)
            set_mode(ha, "Disarmed")
            ha.wait_for_state(ALARM_STATE, "Disarmed", timeout=2)
            ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)
