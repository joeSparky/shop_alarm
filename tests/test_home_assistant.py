import os
import requests

HA_URL = "http://192.168.12.201:8123"
HA_TOKEN = os.environ["HA_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}


def test_home_assistant_api_is_running():
    response = requests.get(
        f"{HA_URL}/api/",
        headers=HEADERS,
        timeout=10,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "API running."


def test_front_door_sensor_exists():
    response = requests.get(
        f"{HA_URL}/api/states/binary_sensor.shop_front_door_opening",
        headers=HEADERS,
        timeout=10,
    )

    assert response.status_code == 200

    state = response.json()["state"]

    assert state in ("on", "off")