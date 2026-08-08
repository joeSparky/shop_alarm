from ha.client import HomeAssistantClient


FRONT_DOOR = "binary_sensor.shop_front_door_opening"


def test_home_assistant_api_is_running():
    with HomeAssistantClient() as ha:
        assert ha.api_status() == "API running."


def test_front_door_sensor_exists():
    with HomeAssistantClient() as ha:
        assert ha.state(FRONT_DOOR) in ("on", "off")
