import asyncio
import signal
from json import loads
from secrets import Secrets as secrets

from gmqtt import Client as MQTTClient
from obswebsocket import obsws
from obswebsocket import requests

obs_client = obsws(secrets.obs_ip, secrets.obs_ws_port, secrets.obs_secret)
obs_client.connect()

STOP = asyncio.Event()

treatbot_active = False  # Used for automatic timeout of the treatbot camera source


def on_connect(client, flags, rc, properties):
    print("Connected")
    for feed in feeds.keys():
        client.subscribe(f"{secrets.aio_user}/feeds/{feed}/json")


async def on_message(client, topic, payload, qos, properties):

    # For some reason when the on_message is an asynchronous function it sends both
    # the topic and the topic/json and we only want the topic/json
    is_it_json = True if topic.split("/")[-1] == "json" else False

    if is_it_json:
        payload_json = loads(payload)
        print(f"RECV MSG: {payload_json['key']=}, {payload_json['last_value']=}")

        # Call the function for that specific feed
        await feeds[payload_json["key"]](payload_json["last_value"])


def on_disconnect(client, packet, exc=None):
    print("Disconnected")


def on_subscribe(client, mid, qos, properties):
    for sub in client.subscriptions:
        print(f"SUBSCRIBED {sub.topic}, {sub.acknowledged=}")


async def treatbot_cam(value):
    enabled = bool(int(value))
    global treatbot_active

    obs_client.call(requests.SetSceneItemRender("TreatBot", enabled, "Common"))

    if enabled:
        treatbot_active = True
        await asyncio.sleep(17)
        if treatbot_active:
            print(
                "Hrm.... the treatbot didn't disable the OBS display. Disabling it..."
            )
            obs_client.call(requests.SetSceneItemRender("TreatBot", False, "Common"))
    else:
        treatbot_active = False


def ask_exit(*args):
    STOP.set()
    obs_client.disconnect()


async def main(client):

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_subscribe = on_subscribe

    mqtt_client.set_auth_credentials(secrets.aio_user, secrets.aio_key)
    await mqtt_client.connect("io.adafruit.com", 8883, ssl=True)

    await STOP.wait()
    await client.disconnect()


if __name__ == "__main__":
    feeds = {
        "dispense-treat-toggle": treatbot_cam,
    }

    loop = asyncio.get_event_loop()

    loop.add_signal_handler(signal.SIGINT, ask_exit)
    loop.add_signal_handler(signal.SIGTERM, ask_exit)

    mqtt_client = MQTTClient("client-id")

    loop.run_until_complete(main(mqtt_client))
