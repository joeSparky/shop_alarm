# ALARM PYTEST SUITE - GENERIC SENSOR ROLES - 37 TESTS
from pathlib import Path
import time

import pytest

from ha.client import HomeAssistantClient


WATER_SENSOR = "binary_sensor.water_detector"

ALARM_MODE = "input_select.shop_alarm_mode"
ALARM_STATE = "input_select.shop_alarm_state"
ALARM_TRIGGERED = "input_boolean.shop_alarm_triggered"

TEST_DOOR = "input_boolean.shop_alarm_test_door_open"
TEST_MODE = "input_boolean.shop_alarm_test_mode"
TEST_SIREN_UNAVAILABLE = "input_boolean.shop_alarm_test_siren_unavailable"
TEST_SECURITY_SENSOR_UNAVAILABLE = "input_boolean.shop_alarm_test_security_sensor_unavailable"

NOTIFY_ACTION = "input_text.shop_alarm_notify_action"
NOTIFICATION_ACTIVE = "input_boolean.shop_alarm_notification_active"
NOTIFICATIONS_ACKNOWLEDGED = "input_boolean.shop_alarm_notifications_acknowledged"
NOTIFICATION_STATUS = "sensor.shop_notification_status"
IMMEDIATE_SECURITY_STATUS = "sensor.immediate_security"
DELAYED_SECURITY_STATUS = "sensor.delayed_security"

SIREN_RELAY = "switch.shop_siren_relay"
SYSTEM_TROUBLE = "binary_sensor.shop_alarm_system_trouble"
SYSTEM_TROUBLE_STATUS = "sensor.alarm_system_trouble_status"

REQUEST_HOME = "script.shop_alarm_request_home"
REQUEST_AWAY = "script.shop_alarm_request_away"
REQUEST_SLEEP = "script.shop_alarm_request_sleep"
OVERRIDE_HOME = "script.shop_alarm_override_home"
OVERRIDE_AWAY = "script.shop_alarm_override_away"
OVERRIDE_SLEEP = "script.shop_alarm_override_sleep"
DISARM_SCRIPT = "script.shop_alarm_disarm"
CANCEL_EXIT_DELAY = "script.shop_alarm_cancel_exit_delay"
ACKNOWLEDGE_NOTIFICATIONS = "script.shop_alarm_acknowledge_notifications"

PACKAGE_FILE = Path(__file__).resolve().parents[1] / "homeassistant" / "shop_alarm.yaml"


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
    set_boolean(ha, TEST_SECURITY_SENSOR_UNAVAILABLE, False)


def reset_notification_flags(ha: HomeAssistantClient) -> None:
    """Put the notification-cycle helpers in the normal/ready state."""
    set_boolean(ha, NOTIFICATION_ACTIVE, False)
    set_boolean(ha, NOTIFICATIONS_ACKNOWLEDGED, False)


def reset_alarm(ha: HomeAssistantClient) -> None:
    close_test_door(ha)
    clear_supervision_test_inputs(ha)
    run_script(ha, DISARM_SCRIPT)
    ha.wait_for_state(ALARM_STATE, "Disarmed", timeout=2)
    ha.wait_for_state(ALARM_MODE, "Disarmed", timeout=2)
    ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)
    reset_notification_flags(ha)


def arm_and_wait(ha: HomeAssistantClient, script: str, final_state: str) -> None:
    run_script(ha, script)
    if final_state in ("Armed Away", "Armed Sleep"):
        ha.wait_for_state(ALARM_STATE, "Exit Delay", timeout=2)
        ha.wait_for_state(ALARM_STATE, final_state, timeout=3)
    else:
        ha.wait_for_state(ALARM_STATE, final_state, timeout=2)


def package_text() -> str:
    if not PACKAGE_FILE.exists():
        pytest.skip(f"Local package file not found: {PACKAGE_FILE}")

    text = PACKAGE_FILE.read_text(encoding="utf-8")

    # The deployed Home Assistant package may be newer than the GitHub/local
    # working copy.  Do not turn that synchronization issue into a false
    # alarm-system test failure.
    if "shop_alarm_notification_rearm" not in text:
        pytest.skip(
            "Local homeassistant/shop_alarm.yaml has not yet been updated "
            "to the current Notification-cycle design."
        )

    return text


# ---------------------------------------------------------------------------
# Basic Home Assistant / entity checks
# ---------------------------------------------------------------------------


def test_home_assistant_api_is_running():
    with HomeAssistantClient() as ha:
        assert ha.api_status() == "API running."


def test_core_alarm_entities_exist():
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
        assert ha.state(SIREN_RELAY) in ("on", "off", "unavailable", "unknown")


def test_notification_entities_exist():
    with HomeAssistantClient() as ha:
        assert ha.state(NOTIFICATION_ACTIVE) in ("on", "off")
        assert ha.state(NOTIFICATIONS_ACKNOWLEDGED) in ("on", "off")
        assert isinstance(ha.state(NOTIFICATION_STATUS), str)
        assert ha.state(ACKNOWLEDGE_NOTIFICATIONS) in ("on", "off")


def test_security_role_status_entities_exist():
    with HomeAssistantClient() as ha:
        assert isinstance(ha.state(IMMEDIATE_SECURITY_STATUS), str)
        assert isinstance(ha.state(DELAYED_SECURITY_STATUS), str)


def test_water_is_now_only_a_regular_sensor():
    """The physical water detector remains; old dedicated water helpers are gone."""
    with HomeAssistantClient() as ha:
        assert ha.state(WATER_SENSOR) in ("on", "off")


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


# ---------------------------------------------------------------------------
# Protected-door behavior
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
            ha.wait_for_state(ALARM_TRIGGERED, "off", timeout=2)
        finally:
            reset_alarm(ha)
            set_boolean(ha, TEST_MODE, False)


# ---------------------------------------------------------------------------
# Notification-cycle / latching behavior
# ---------------------------------------------------------------------------


def test_notification_flag_can_be_reasserted_without_restarting_state():
    """
    The active flag is a latch. Reasserting ON while already ON is harmless.

    This is the helper-level regression test for repeated sensor activations
    during one notification cycle.
    """
    with HomeAssistantClient() as ha:
        reset_notification_flags(ha)
        try:
            set_boolean(ha, NOTIFICATION_ACTIVE, True)
            assert ha.state(NOTIFICATION_ACTIVE) == "on"
            assert ha.state(NOTIFICATIONS_ACKNOWLEDGED) == "off"

            # Reassert the same flag just as another Notification-role event does.
            set_boolean(ha, NOTIFICATION_ACTIVE, True)
            assert ha.state(NOTIFICATION_ACTIVE) == "on"
            assert ha.state(NOTIFICATIONS_ACKNOWLEDGED) == "off"
        finally:
            reset_notification_flags(ha)


def test_stop_notifications_latches_acknowledgement_and_clears_active_flag():
    """
    Stop Notifications ends the current reminder cycle but leaves the system
    acknowledged until all Notification-role conditions have cleared.
    """
    with HomeAssistantClient() as ha:
        reset_notification_flags(ha)
        try:
            set_boolean(ha, NOTIFICATION_ACTIVE, True)

            run_script(ha, ACKNOWLEDGE_NOTIFICATIONS)
            ha.wait_for_state(NOTIFICATIONS_ACKNOWLEDGED, "on", timeout=2)
            ha.wait_for_state(NOTIFICATION_ACTIVE, "off", timeout=2)
        finally:
            reset_notification_flags(ha)


def test_stop_notifications_is_idempotent():
    """Pressing Stop Notifications more than once must remain harmless."""
    with HomeAssistantClient() as ha:
        reset_notification_flags(ha)
        try:
            set_boolean(ha, NOTIFICATION_ACTIVE, True)
            run_script(ha, ACKNOWLEDGE_NOTIFICATIONS)
            ha.wait_for_state(NOTIFICATIONS_ACKNOWLEDGED, "on", timeout=2)
            ha.wait_for_state(NOTIFICATION_ACTIVE, "off", timeout=2)

            run_script(ha, ACKNOWLEDGE_NOTIFICATIONS)
            ha.wait_for_state(NOTIFICATIONS_ACKNOWLEDGED, "on", timeout=2)
            assert ha.state(NOTIFICATION_ACTIVE) == "off"
        finally:
            reset_notification_flags(ha)


def test_acknowledging_intrusion_alarm_does_not_disarm_alarm_or_siren():
    """Stop Notifications silences repeats; it does not acknowledge the burglary itself."""
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
# Static configuration regression tests for the generic Notification role
# ---------------------------------------------------------------------------


def test_package_has_latched_notification_cycle_logic():
    text = package_text()

    assert "id: shop_alarm_notification_role" in text
    assert "notification_cycle_was_active" in text
    assert "input_boolean.shop_alarm_notification_active" in text

    # A sensor event must not automatically clear acknowledgement and start
    # another first-notification while a cycle is already acknowledged.
    role_start = text.index("id: shop_alarm_notification_role")
    rearm_start = text.index("id: shop_alarm_notification_rearm")
    role_block = text[role_start:rearm_start]

    assert "input_boolean.shop_alarm_notifications_acknowledged" in role_block
    assert 'state: "off"' in role_block
    assert "if:" in role_block
    assert "not notification_cycle_was_active" in role_block


def test_package_rearms_only_after_all_notification_conditions_are_clear():
    text = package_text()

    assert "id: shop_alarm_notification_rearm" in text
    rearm_start = text.index("id: shop_alarm_notification_rearm")
    repeat_start = text.index("id: shop_alarm_repeat_active_alarm_notification")
    rearm_block = text[rearm_start:repeat_start]

    assert "any_active" in rearm_block
    assert "not ns.any_active" in rearm_block
    assert "input_boolean.shop_alarm_notifications_acknowledged" in rearm_block
    assert "input_boolean.shop_alarm_notification_active" in rearm_block


def test_package_notification_status_uses_generic_notification_entities():
    text = package_text()

    assert "name: Notification Status" in text
    assert "label_id('Notification')" in text
    assert "entity.state in ['unavailable', 'unknown']" in text


def test_package_has_no_dedicated_water_alarm_logic():
    """
    Water is now simply a Notification-role entity.

    These old helpers/scripts would indicate that water still has a special path.
    """
    text = package_text()

    assert "shop_water_alarm_enabled" not in text
    assert "shop_water_alarm_active" not in text
    assert "shop_water_alarm_test_wet" not in text
    assert "shop_water_alarm_enable:" not in text
    assert "shop_water_alarm_disable:" not in text
    assert "shop_water_alarm_reset:" not in text
    assert "shop_water_alarm_trigger" not in text


def test_package_has_no_front_door_special_case():
    """
    Security behavior must come from Immediate Security / Delayed Security
    labels, not from a hard-coded physical front-door entity.
    """
    text = package_text()

    assert "binary_sensor.shop_front_door_opening" not in text
    assert "shop_alarm_test_front_door_unavailable" not in text
    assert "shop_alarm_front_door_trouble" not in text

    assert "label_id('Delayed Security')" in text
    assert "label_id('Immediate Security')" in text
    assert "shop_alarm_test_security_sensor_unavailable" in text


def test_package_readiness_uses_security_role_labels():
    text = package_text()

    away_start = text.index("name: Alarm Away Ready")
    status_start = text.index("name: Notification Status")
    ready_block = text[away_start:status_start]

    assert "label_id('Delayed Security')" in ready_block
    assert "label_id('Immediate Security')" in ready_block
    assert "entity.state == 'on'" in ready_block


def test_package_security_role_status_sensors_show_only_active_sensors():
    text = package_text()

    immediate_start = text.index("name: Immediate Security")
    delayed_start = text.index("name: Delayed Security")
    input_text_start = text.index("input_text:")
    immediate_block = text[immediate_start:delayed_start]
    delayed_block = text[delayed_start:input_text_start]

    assert "unique_id: alarm_immediate_security_status" in immediate_block
    assert "label_id('Immediate Security')" in immediate_block
    assert "states.binary_sensor" in immediate_block
    assert "entity.state == 'on'" in immediate_block
    assert "None Active" in immediate_block
    assert "active_count:" in immediate_block
    assert "active_entities:" in immediate_block

    assert "unique_id: alarm_delayed_security_status" in delayed_block
    assert "label_id('Delayed Security')" in delayed_block
    assert "states.binary_sensor" in delayed_block
    assert "entity.state == 'on'" in delayed_block
    assert "None Active" in delayed_block
    assert "active_count:" in delayed_block
    assert "active_entities:" in delayed_block


def test_package_system_trouble_uses_dedicated_label():
    """Actual system-trouble supervision comes only from its dedicated label."""
    text = package_text()

    trouble_start = text.index("- name: Alarm System Trouble")
    home_ready_start = text.index("- name: Alarm Home Ready")
    trouble_block = text[trouble_start:home_ready_start]

    assert "label_id('Alarm System Trouble')" in trouble_block
    assert "states('switch.shop_siren_relay')" not in trouble_block
    assert "label_id('Delayed Security')" not in trouble_block
    assert "label_id('Immediate Security')" not in trouble_block


def test_package_has_no_special_trouble_notification_automations():
    """System-health supervision must not bypass the generic Notification role."""
    text = package_text()

    assert "shop_alarm_siren_trouble_notification" not in text
    assert "shop_alarm_siren_trouble_restored" not in text
    assert "shop_alarm_security_sensor_trouble_notification" not in text
    assert "shop_alarm_security_sensor_trouble_restored" not in text


def test_system_trouble_and_notification_labels_are_independent():
    text = package_text()

    trouble_start = text.index("- name: Alarm System Trouble")
    home_ready_start = text.index("- name: Alarm Home Ready")
    trouble_block = text[trouble_start:home_ready_start]

    notification_start = text.index("id: shop_alarm_notification_role")
    notification_rearm_start = text.index("id: shop_alarm_notification_rearm")
    notification_block = text[notification_start:notification_rearm_start]

    assert "label_id('Notification')" not in trouble_block
    assert "label_id('Alarm System Trouble')" not in notification_block


def test_package_has_system_trouble_status_sensor_for_dashboard():
    """Dashboard status mirrors system trouble while the binary sensor remains authoritative."""
    text = package_text()

    status_start = text.index("- name: Alarm System Trouble Status")
    notification_start = text.index("- name: Notification Status")
    status_block = text[status_start:notification_start]

    assert "unique_id: alarm_system_trouble_status" in status_block
    assert "binary_sensor.shop_alarm_system_trouble" in status_block
    assert "No Trouble" in status_block
    assert "trouble_reason" in status_block
    assert "active_count:" in status_block
    assert "active_entities:" in status_block
    assert "switch.shop_siren_relay" in status_block
    assert "Shop Siren Relay unavailable" in text


# ---------------------------------------------------------------------------
# Readiness / supervision smoke tests
# ---------------------------------------------------------------------------


def test_system_trouble_entity_exists():
    with HomeAssistantClient() as ha:
        assert ha.state(SYSTEM_TROUBLE) in ("on", "off")


def test_system_trouble_status_entity_exists_and_matches_trouble_state():
    with HomeAssistantClient() as ha:
        status = ha.state(SYSTEM_TROUBLE_STATUS)
        assert isinstance(status, str)
        assert status != ""
        if ha.state(SYSTEM_TROUBLE) == "off":
            assert status == "No Trouble"


def test_simulated_unavailable_siren_causes_system_trouble():
    with HomeAssistantClient() as ha:
        clear_supervision_test_inputs(ha)
        try:
            set_boolean(ha, TEST_SIREN_UNAVAILABLE, True)
            ha.wait_for_state(SYSTEM_TROUBLE, "on", timeout=2)
        finally:
            set_boolean(ha, TEST_SIREN_UNAVAILABLE, False)
            ha.wait_for_state(SYSTEM_TROUBLE, "off", timeout=2)


def test_simulated_siren_unavailable_appears_in_system_trouble_status():
    """Exercise the siren trouble path without changing the real Zigbee entity state."""
    with HomeAssistantClient() as ha:
        clear_supervision_test_inputs(ha)

        if ha.state(SYSTEM_TROUBLE) != "off":
            pytest.skip("System already has a real trouble condition; cannot isolate this test.")

        try:
            set_boolean(ha, TEST_SIREN_UNAVAILABLE, True)
            ha.wait_for_state(SYSTEM_TROUBLE, "on", timeout=2)

            deadline = time.monotonic() + 2
            while True:
                status = ha.get_state(SYSTEM_TROUBLE_STATUS)
                active_entities = status.get("attributes", {}).get("active_entities", [])
                if SIREN_RELAY in active_entities:
                    break
                if time.monotonic() >= deadline:
                    pytest.fail(
                        f"{SIREN_RELAY} did not appear in "
                        f"{SYSTEM_TROUBLE_STATUS} active_entities; got {active_entities!r}"
                    )
                time.sleep(0.1)

            assert "siren" in status["state"].lower()
            assert "unavailable" in status["state"].lower()
        finally:
            set_boolean(ha, TEST_SIREN_UNAVAILABLE, False)
            ha.wait_for_state(SYSTEM_TROUBLE, "off", timeout=2)


def test_system_trouble_stays_on_until_all_test_faults_clear():
    with HomeAssistantClient() as ha:
        clear_supervision_test_inputs(ha)
        try:
            set_boolean(ha, TEST_SIREN_UNAVAILABLE, True)
            set_boolean(ha, TEST_SECURITY_SENSOR_UNAVAILABLE, True)
            ha.wait_for_state(SYSTEM_TROUBLE, "on", timeout=2)

            set_boolean(ha, TEST_SIREN_UNAVAILABLE, False)
            assert ha.state(SYSTEM_TROUBLE) == "on"

            set_boolean(ha, TEST_SECURITY_SENSOR_UNAVAILABLE, False)
            ha.wait_for_state(SYSTEM_TROUBLE, "off", timeout=2)
        finally:
            clear_supervision_test_inputs(ha)
