from ha.client import HomeAssistantClient


FRONT_DOOR = "binary_sensor.shop_front_door_opening"
ALARM_MODE = "input_select.shop_alarm_mode"
ALARM_STATE = "input_select.shop_alarm_state"
ALARM_TRIGGERED = "input_boolean.shop_alarm_triggered"
TEST_DOOR = "input_boolean.shop_alarm_test_door_open"
TEST_MODE = "input_boolean.shop_alarm_test_mode"
NOTIFY_ACTION = "input_text.shop_alarm_notify_action"
NOTIFICATIONS_ACKNOWLEDGED = "input_boolean.shop_alarm_notifications_acknowledged"
SIREN_RELAY = "switch.shop_siren_relay"
SYSTEM_TROUBLE = "binary_sensor.shop_alarm_system_trouble"
TEST_SIREN_UNAVAILABLE = "input_boolean.shop_alarm_test_siren_unavailable"
TEST_FRONT_DOOR_UNAVAILABLE = "input_boolean.shop_alarm_test_front_door_unavailable"

REQUEST_HOME = "script.shop_alarm_request_home"
REQUEST_AWAY = "script.shop_alarm_request_away"
REQUEST_SLEEP = "script.shop_alarm_request_sleep"
OVERRIDE_HOME = "script.shop_alarm_override_home"
OVERRIDE_AWAY = "script.shop_alarm_override_away"
OVERRIDE_SLEEP = "script.shop_alarm_override_sleep"
DISARM_SCRIPT = "script.shop_alarm_disarm"
CANCEL_EXIT_DELAY = "script.shop_alarm_cancel_exit_delay"
ACKNOWLEDGE_NOTIFICATIONS = "script.shop_alarm_acknowledge_notifications"

WATER_SENSOR = "binary_sensor.water_detector"
WATER_ENABLED = "input_boolean.shop_water_alarm_enabled"
WATER_ACTIVE = "input_boolean.shop_water_alarm_active"
WATER_TEST_WET = "input_boolean.shop_water_alarm_test_wet"
WATER_ENABLE_SCRIPT = "script.shop_water_alarm_enable"
WATER_DISABLE_SCRIPT = "script.shop_water_alarm_disable"
WATER_RESET_SCRIPT = "script.shop_water_alarm_reset"


def set_mode_directly(ha: HomeAssistantClient, mode: str) -> None:
    """Direct helper edit used only to verify that Mode is status, not a command."""
    ha.call_service(
        "input_select",
        "select_option",
        {"entity_id": ALARM_MODE, "option": mode},
    )


def set_boolean(ha: HomeAssistantClient, entity_id: str, on: bool) -> None:
    service = "turn_on" if on else "turn_off"
    target_state = "on" if on else "off"
    ha.call_service("input_boolean", service, {"entity_id": entity_id})
    ha.wait_for_state(entity_id, target_state, timeout=2)


def run_script(ha: HomeAssistantClient, entity_id: str) -> None:
    ha.call_service("script", "turn_on", {"entity_id": entity_id})


def close_test_door(ha: HomeAssistantClient) -> None:
    set_boolean(ha, TEST_DOOR, False)


def open_test_door(ha: HomeAssistantClient) -> None:
    set_boolean(ha, TEST_DOOR, True)


def clear_supervision_test_inputs(ha: HomeAssistantClient) -> None:
    set_boolean(ha, TEST_SIREN_UNAVAILABLE, False)
    set_boolean(ha, TEST_FRONT_DOOR_UNAVAILABLE, False)


def reset_alarm(ha: HomeAssistantClient) -> None:
    close_test_door(ha)
    clear_supervision_test_inputs(ha)
    run_script(ha, DISARM_SCRIPT)
    ha.wait_for_state(ALARM_STATE, "Disarmed", timeout=2)
    ha.wait_for_state(ALARM_MODE, "Disarmed", timeout=2)
    ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)
    set_boolean(ha, NOTIFICATIONS_ACKNOWLEDGED, False)


def arm_and_wait(ha: HomeAssistantClient, script: str, final_state: str) -> None:
    run_script(ha, script)
    if final_state in ("Armed Away", "Armed Sleep"):
        ha.wait_for_state(ALARM_STATE, "Exit Delay", timeout=2)
        ha.wait_for_state(ALARM_STATE, final_state, timeout=3)
    else:
        ha.wait_for_state(ALARM_STATE, final_state, timeout=2)


def set_test_water_wet(ha: HomeAssistantClient, wet: bool) -> None:
    set_boolean(ha, WATER_TEST_WET, wet)


def reset_water_alarm(ha: HomeAssistantClient) -> None:
    set_test_water_wet(ha, False)
    run_script(ha, WATER_ENABLE_SCRIPT)
    ha.wait_for_state(WATER_ENABLED, "on", timeout=2)

    if ha.state(WATER_ACTIVE) == "on":
        run_script(ha, WATER_RESET_SCRIPT)
        ha.wait_for_state(WATER_ACTIVE, "off", timeout=2)

    if ha.state(SIREN_RELAY) in ("on", "off"):
        ha.wait_for_state(SIREN_RELAY, "off", timeout=2)

    set_boolean(ha, NOTIFICATIONS_ACKNOWLEDGED, False)


# ---------------------------------------------------------------------------
# Basic Home Assistant / entity checks
# ---------------------------------------------------------------------------


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


def test_shop_alarm_entities_exist():
    with HomeAssistantClient() as ha:
        assert ha.state(ALARM_MODE) in ("Disarmed", "Home", "Away", "Sleep")
        assert ha.state(ALARM_STATE) in (
            "Disarmed",
            "Armed Home",
            "Exit Delay",
            "Armed Away",
            "Armed Sleep",
            "Entry Delay",
            "Fault",
            "Alarm",
        )
        assert ha.state(ALARM_TRIGGERED) in ("on", "off")


def test_command_scripts_exist():
    with HomeAssistantClient() as ha:
        for entity_id in (
            REQUEST_HOME,
            REQUEST_AWAY,
            REQUEST_SLEEP,
            OVERRIDE_HOME,
            OVERRIDE_AWAY,
            OVERRIDE_SLEEP,
            DISARM_SCRIPT,
            CANCEL_EXIT_DELAY,
        ):
            assert ha.state(entity_id) in ("on", "off")


def test_shop_alarm_notify_action_entity_exists():
    with HomeAssistantClient() as ha:
        assert isinstance(ha.state(NOTIFY_ACTION), str)


def test_notification_acknowledgement_entities_exist():
    with HomeAssistantClient() as ha:
        assert ha.state(NOTIFICATIONS_ACKNOWLEDGED) in ("on", "off")
        assert ha.state(ACKNOWLEDGE_NOTIFICATIONS) in ("on", "off")


def test_mobile_app_notify_action_is_configured():
    with HomeAssistantClient() as ha:
        candidates = ha.service_names("notify", prefix="mobile_app_")
        assert "mobile_app_iphone" in candidates, (
            "Expected Home Assistant notification service "
            "'mobile_app_iphone'; "
            f"found {candidates!r}."
        )

        action = "notify.mobile_app_iphone"
        ha.call_service(
            "input_text",
            "set_value",
            {"entity_id": NOTIFY_ACTION, "value": action},
        )
        ha.wait_for_state(NOTIFY_ACTION, action, timeout=2)


# ---------------------------------------------------------------------------
# State-machine command interface
# ---------------------------------------------------------------------------


def test_direct_mode_edit_does_not_arm_system():
    """Mode is status/target information, not the command API."""
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_mode_directly(ha, "Away")
        ha.wait_for_state(ALARM_MODE, "Disarmed", timeout=2)
        assert ha.state(ALARM_STATE) == "Disarmed"


def test_home_command_arms_home_immediately():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        try:
            run_script(ha, REQUEST_HOME)
            ha.wait_for_state(ALARM_STATE, "Armed Home", timeout=2)
            assert ha.state(ALARM_MODE) == "Home"
            assert ha.state(ALARM_TRIGGERED) == "off"
        finally:
            reset_alarm(ha)


def test_away_command_has_exit_delay_then_arms():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            run_script(ha, REQUEST_AWAY)
            ha.wait_for_state(ALARM_STATE, "Exit Delay", timeout=2)
            assert ha.state(ALARM_MODE) == "Away"
            ha.wait_for_state(ALARM_STATE, "Armed Away", timeout=3)
            assert ha.state(ALARM_TRIGGERED) == "off"
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


def test_sleep_command_has_exit_delay_then_arms():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            run_script(ha, REQUEST_SLEEP)
            ha.wait_for_state(ALARM_STATE, "Exit Delay", timeout=2)
            assert ha.state(ALARM_MODE) == "Sleep"
            ha.wait_for_state(ALARM_STATE, "Armed Sleep", timeout=3)
            assert ha.state(ALARM_TRIGGERED) == "off"
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


def test_cancel_exit_delay_disarms_without_waiting_for_arm():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            run_script(ha, REQUEST_AWAY)
            ha.wait_for_state(ALARM_STATE, "Exit Delay", timeout=2)
            run_script(ha, CANCEL_EXIT_DELAY)
            ha.wait_for_state(ALARM_STATE, "Disarmed", timeout=2)
            ha.wait_for_state(ALARM_MODE, "Disarmed", timeout=2)
            assert ha.state(ALARM_TRIGGERED) == "off"
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


def test_new_arm_request_is_rejected_while_already_armed():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        try:
            arm_and_wait(ha, REQUEST_HOME, "Armed Home")
            run_script(ha, REQUEST_AWAY)
            # The authoritative state/mode must remain Home.
            assert ha.state(ALARM_STATE) == "Armed Home"
            assert ha.state(ALARM_MODE) == "Home"
        finally:
            reset_alarm(ha)


# ---------------------------------------------------------------------------
# Protected-door behavior: every armed mode uses Entry Delay
# ---------------------------------------------------------------------------


def _assert_armed_mode_door_runs_entry_delay_then_alarm(
    request_script: str,
    armed_state: str,
):
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            arm_and_wait(ha, request_script, armed_state)
            open_test_door(ha)
            ha.wait_for_state(ALARM_STATE, "Entry Delay", timeout=2)
            ha.wait_for_state(ALARM_STATE, "Alarm", timeout=3)
            assert ha.state(ALARM_TRIGGERED) == "on"
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


def test_home_door_runs_entry_delay_then_alarm():
    _assert_armed_mode_door_runs_entry_delay_then_alarm(REQUEST_HOME, "Armed Home")


def test_away_door_runs_entry_delay_then_alarm():
    _assert_armed_mode_door_runs_entry_delay_then_alarm(REQUEST_AWAY, "Armed Away")


def test_sleep_door_runs_entry_delay_then_alarm():
    _assert_armed_mode_door_runs_entry_delay_then_alarm(REQUEST_SLEEP, "Armed Sleep")


def test_disarm_during_entry_delay_prevents_alarm():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            arm_and_wait(ha, REQUEST_AWAY, "Armed Away")
            open_test_door(ha)
            ha.wait_for_state(ALARM_STATE, "Entry Delay", timeout=2)
            run_script(ha, DISARM_SCRIPT)
            ha.wait_for_state(ALARM_STATE, "Disarmed", timeout=2)
            ha.wait_for_state(ALARM_MODE, "Disarmed", timeout=2)
            ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


# ---------------------------------------------------------------------------
# Repeating-notification acknowledgement
# ---------------------------------------------------------------------------


def test_acknowledge_notifications_script_sets_acknowledged():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        try:
            run_script(ha, ACKNOWLEDGE_NOTIFICATIONS)
            ha.wait_for_state(NOTIFICATIONS_ACKNOWLEDGED, "on", timeout=2)
        finally:
            set_boolean(ha, NOTIFICATIONS_ACKNOWLEDGED, False)


def test_new_door_alarm_clears_notification_acknowledgement():
    """A new intrusion alarm must resume notifications after an earlier acknowledgement."""
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            arm_and_wait(ha, REQUEST_HOME, "Armed Home")
            run_script(ha, ACKNOWLEDGE_NOTIFICATIONS)
            ha.wait_for_state(NOTIFICATIONS_ACKNOWLEDGED, "on", timeout=2)

            open_test_door(ha)
            ha.wait_for_state(ALARM_STATE, "Entry Delay", timeout=2)
            ha.wait_for_state(ALARM_STATE, "Alarm", timeout=3)
            ha.wait_for_state(NOTIFICATIONS_ACKNOWLEDGED, "off", timeout=2)
            assert ha.state(ALARM_TRIGGERED) == "on"
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


def test_acknowledging_door_alarm_does_not_clear_alarm_or_siren():
    """Stop Notifications must silence repeats without disarming the alarm."""
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            arm_and_wait(ha, REQUEST_HOME, "Armed Home")
            open_test_door(ha)
            ha.wait_for_state(ALARM_STATE, "Alarm", timeout=3)
            ha.wait_for_state(ALARM_TRIGGERED, "on", timeout=2)
            ha.wait_for_state(SIREN_RELAY, "on", timeout=2)

            run_script(ha, ACKNOWLEDGE_NOTIFICATIONS)
            ha.wait_for_state(NOTIFICATIONS_ACKNOWLEDGED, "on", timeout=2)
            assert ha.state(ALARM_STATE) == "Alarm"
            assert ha.state(ALARM_TRIGGERED) == "on"
            assert ha.state(SIREN_RELAY) == "on"
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


# ---------------------------------------------------------------------------
# Readiness faults and explicit override
# ---------------------------------------------------------------------------


def test_away_with_open_virtual_door_stays_disarmed():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            open_test_door(ha)
            run_script(ha, REQUEST_AWAY)
            ha.wait_for_state(ALARM_STATE, "Disarmed", timeout=2)
            ha.wait_for_state(ALARM_MODE, "Disarmed", timeout=2)
            assert ha.state(TEST_DOOR) == "on"
            assert ha.state(ALARM_TRIGGERED) == "off"
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


def test_sleep_with_open_virtual_door_stays_disarmed():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            open_test_door(ha)
            run_script(ha, REQUEST_SLEEP)
            ha.wait_for_state(ALARM_STATE, "Disarmed", timeout=2)
            ha.wait_for_state(ALARM_MODE, "Disarmed", timeout=2)
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


def test_away_open_door_fault_can_be_overridden():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            open_test_door(ha)
            run_script(ha, OVERRIDE_AWAY)
            ha.wait_for_state(ALARM_STATE, "Exit Delay", timeout=2)
            ha.wait_for_state(ALARM_STATE, "Armed Away", timeout=3)
            assert ha.state(ALARM_MODE) == "Away"
            assert ha.state(TEST_DOOR) == "on"
            assert ha.state(ALARM_TRIGGERED) == "off"
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


def test_simulated_unavailable_siren_blocks_normal_away():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            set_boolean(ha, TEST_SIREN_UNAVAILABLE, True)
            ha.wait_for_state(SYSTEM_TROUBLE, "on", timeout=2)
            run_script(ha, REQUEST_AWAY)
            ha.wait_for_state(ALARM_STATE, "Disarmed", timeout=2)
            ha.wait_for_state(ALARM_MODE, "Disarmed", timeout=2)
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


def test_simulated_unavailable_siren_override_away_still_arms():
    """The arming state machine must not depend on commanding the siren relay."""
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            set_boolean(ha, TEST_SIREN_UNAVAILABLE, True)
            ha.wait_for_state(SYSTEM_TROUBLE, "on", timeout=2)
            run_script(ha, OVERRIDE_AWAY)
            ha.wait_for_state(ALARM_STATE, "Exit Delay", timeout=2)
            ha.wait_for_state(ALARM_STATE, "Armed Away", timeout=3)
            assert ha.state(ALARM_MODE) == "Away"
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


def test_simulated_unavailable_siren_override_home_still_arms():
    with HomeAssistantClient() as ha:
        reset_alarm(ha)
        try:
            set_boolean(ha, TEST_SIREN_UNAVAILABLE, True)
            ha.wait_for_state(SYSTEM_TROUBLE, "on", timeout=2)
            run_script(ha, OVERRIDE_HOME)
            ha.wait_for_state(ALARM_STATE, "Armed Home", timeout=2)
            assert ha.state(ALARM_MODE) == "Home"
        finally:
            reset_alarm(ha)


# ---------------------------------------------------------------------------
# Supervision / trouble entity
# ---------------------------------------------------------------------------


def test_system_trouble_entity_exists():
    with HomeAssistantClient() as ha:
        assert ha.state(SYSTEM_TROUBLE) in ("on", "off")


def test_supervision_test_inputs_exist():
    with HomeAssistantClient() as ha:
        assert ha.state(TEST_SIREN_UNAVAILABLE) in ("on", "off")
        assert ha.state(TEST_FRONT_DOOR_UNAVAILABLE) in ("on", "off")


def test_healthy_supervised_devices_clear_system_trouble():
    with HomeAssistantClient() as ha:
        clear_supervision_test_inputs(ha)
        assert ha.state(SIREN_RELAY) in ("on", "off")
        assert ha.state(FRONT_DOOR) in ("on", "off")
        ha.wait_for_state(SYSTEM_TROUBLE, "off", timeout=2)


def test_simulated_unavailable_siren_causes_system_trouble():
    with HomeAssistantClient() as ha:
        clear_supervision_test_inputs(ha)
        try:
            set_boolean(ha, TEST_SIREN_UNAVAILABLE, True)
            ha.wait_for_state(SYSTEM_TROUBLE, "on", timeout=2)
        finally:
            set_boolean(ha, TEST_SIREN_UNAVAILABLE, False)
            ha.wait_for_state(SYSTEM_TROUBLE, "off", timeout=2)


def test_simulated_unavailable_front_door_causes_system_trouble():
    with HomeAssistantClient() as ha:
        clear_supervision_test_inputs(ha)
        try:
            set_boolean(ha, TEST_FRONT_DOOR_UNAVAILABLE, True)
            ha.wait_for_state(SYSTEM_TROUBLE, "on", timeout=2)
        finally:
            set_boolean(ha, TEST_FRONT_DOOR_UNAVAILABLE, False)
            ha.wait_for_state(SYSTEM_TROUBLE, "off", timeout=2)


def test_system_trouble_stays_on_until_all_faults_clear():
    with HomeAssistantClient() as ha:
        clear_supervision_test_inputs(ha)
        try:
            set_boolean(ha, TEST_SIREN_UNAVAILABLE, True)
            set_boolean(ha, TEST_FRONT_DOOR_UNAVAILABLE, True)
            ha.wait_for_state(SYSTEM_TROUBLE, "on", timeout=2)

            set_boolean(ha, TEST_SIREN_UNAVAILABLE, False)
            assert ha.state(SYSTEM_TROUBLE) == "on"

            set_boolean(ha, TEST_FRONT_DOOR_UNAVAILABLE, False)
            ha.wait_for_state(SYSTEM_TROUBLE, "off", timeout=2)
        finally:
            clear_supervision_test_inputs(ha)


# ---------------------------------------------------------------------------
# Water alarm regression tests retained from the existing suite
# ---------------------------------------------------------------------------


def test_water_alarm_entities_exist():
    with HomeAssistantClient() as ha:
        assert ha.state(WATER_SENSOR) in ("on", "off")
        assert ha.state(WATER_ENABLED) in ("on", "off")
        assert ha.state(WATER_ACTIVE) in ("on", "off")
        assert ha.state(WATER_TEST_WET) in ("on", "off")
        assert ha.state(SIREN_RELAY) in ("on", "off")


def test_water_alarm_disabled_still_reports_wet_without_siren():
    with HomeAssistantClient() as ha:
        reset_water_alarm(ha)
        try:
            run_script(ha, WATER_DISABLE_SCRIPT)
            ha.wait_for_state(WATER_ENABLED, "off", timeout=2)
            ha.wait_for_state(SIREN_RELAY, "off", timeout=2)

            set_test_water_wet(ha, True)

            assert ha.state(WATER_TEST_WET) == "on"
            assert ha.state(WATER_ENABLED) == "off"
            assert ha.state(WATER_ACTIVE) == "off"
            assert ha.state(SIREN_RELAY) == "off"
        finally:
            set_test_water_wet(ha, False)
            run_script(ha, WATER_ENABLE_SCRIPT)
            ha.wait_for_state(WATER_ENABLED, "on", timeout=2)


def test_water_alarm_enable_while_wet_triggers_immediately():
    with HomeAssistantClient() as ha:
        reset_water_alarm(ha)
        try:
            run_script(ha, WATER_DISABLE_SCRIPT)
            ha.wait_for_state(WATER_ENABLED, "off", timeout=2)

            set_test_water_wet(ha, True)
            assert ha.state(WATER_ACTIVE) == "off"
            assert ha.state(SIREN_RELAY) == "off"

            run_script(ha, WATER_ENABLE_SCRIPT)
            ha.wait_for_state(WATER_ENABLED, "on", timeout=2)
            ha.wait_for_state(WATER_ACTIVE, "on", timeout=2)
            ha.wait_for_state(SIREN_RELAY, "on", timeout=2)
        finally:
            set_test_water_wet(ha, False)
            run_script(ha, WATER_RESET_SCRIPT)
            ha.wait_for_state(WATER_ACTIVE, "off", timeout=2)
            ha.wait_for_state(SIREN_RELAY, "off", timeout=2)


def test_water_alarm_latches_after_sensor_returns_dry():
    with HomeAssistantClient() as ha:
        reset_water_alarm(ha)
        try:
            set_test_water_wet(ha, True)
            ha.wait_for_state(WATER_ACTIVE, "on", timeout=2)
            ha.wait_for_state(SIREN_RELAY, "on", timeout=2)

            set_test_water_wet(ha, False)

            assert ha.state(WATER_TEST_WET) == "off"
            assert ha.state(WATER_ACTIVE) == "on"
            assert ha.state(SIREN_RELAY) == "on"
        finally:
            run_script(ha, WATER_RESET_SCRIPT)
            ha.wait_for_state(WATER_ACTIVE, "off", timeout=2)
            ha.wait_for_state(SIREN_RELAY, "off", timeout=2)


def test_water_alarm_reset_requires_dry_sensor():
    with HomeAssistantClient() as ha:
        reset_water_alarm(ha)
        try:
            set_test_water_wet(ha, True)
            ha.wait_for_state(WATER_ACTIVE, "on", timeout=2)
            ha.wait_for_state(SIREN_RELAY, "on", timeout=2)

            run_script(ha, WATER_RESET_SCRIPT)
            assert ha.state(WATER_TEST_WET) == "on"
            assert ha.state(WATER_ACTIVE) == "on"
            assert ha.state(SIREN_RELAY) == "on"

            set_test_water_wet(ha, False)
            run_script(ha, WATER_RESET_SCRIPT)
            ha.wait_for_state(WATER_ACTIVE, "off", timeout=2)
            ha.wait_for_state(SIREN_RELAY, "off", timeout=2)
        finally:
            set_test_water_wet(ha, False)
            if ha.state(WATER_ACTIVE) == "on":
                run_script(ha, WATER_RESET_SCRIPT)


def test_new_water_alarm_clears_notification_acknowledgement():
    """A new water alarm must resume notifications after an earlier acknowledgement."""
    with HomeAssistantClient() as ha:
        reset_water_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            run_script(ha, ACKNOWLEDGE_NOTIFICATIONS)
            ha.wait_for_state(NOTIFICATIONS_ACKNOWLEDGED, "on", timeout=2)

            set_test_water_wet(ha, True)
            ha.wait_for_state(WATER_ACTIVE, "on", timeout=2)
            ha.wait_for_state(NOTIFICATIONS_ACKNOWLEDGED, "off", timeout=2)
            ha.wait_for_state(SIREN_RELAY, "on", timeout=2)
        finally:
            set_test_water_wet(ha, False)
            if ha.state(WATER_ACTIVE) == "on":
                run_script(ha, WATER_RESET_SCRIPT)
                ha.wait_for_state(WATER_ACTIVE, "off", timeout=2)
            set_boolean(ha, NOTIFICATIONS_ACKNOWLEDGED, False)
            set_boolean(ha, TEST_MODE, False)


def test_acknowledging_water_alarm_does_not_reset_water_alarm_or_siren():
    """Stop Notifications must not reset the latched water alarm."""
    with HomeAssistantClient() as ha:
        reset_water_alarm(ha)
        set_boolean(ha, TEST_MODE, True)
        try:
            set_test_water_wet(ha, True)
            ha.wait_for_state(WATER_ACTIVE, "on", timeout=2)
            ha.wait_for_state(SIREN_RELAY, "on", timeout=2)

            run_script(ha, ACKNOWLEDGE_NOTIFICATIONS)
            ha.wait_for_state(NOTIFICATIONS_ACKNOWLEDGED, "on", timeout=2)
            assert ha.state(WATER_ACTIVE) == "on"
            assert ha.state(SIREN_RELAY) == "on"
        finally:
            set_test_water_wet(ha, False)
            if ha.state(WATER_ACTIVE) == "on":
                run_script(ha, WATER_RESET_SCRIPT)
                ha.wait_for_state(WATER_ACTIVE, "off", timeout=2)
                ha.wait_for_state(SIREN_RELAY, "off", timeout=2)
            set_boolean(ha, NOTIFICATIONS_ACKNOWLEDGED, False)
            set_boolean(ha, TEST_MODE, False)
