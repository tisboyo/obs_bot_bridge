import asyncio
import signal
from secrets import Secrets as secrets
from secrets import Settings
from secrets import Sources
from time import sleep

from gmqtt import Client as MQTTClient
from obswebsocket import obsws
from obswebsocket import requests
from obswebsocket.exceptions import ConnectionFailure


def get_obs_client():
    obs_client = obsws(secrets.obs_ip, secrets.obs_ws_port, secrets.obs_secret)

    while True:
        try:
            obs_client.connect()
            return obs_client
        except ConnectionFailure:
            print("OBS Connection Failure... sleeping 5 seconds.")
            sleep(5)


def on_connect(client, flags, rc, properties):
    print("Connected")
    for feed in feeds.keys():
        client.subscribe(feed)


async def on_message(client, topic, payload, qos, properties):

    print(f"RECV MSG: {topic=}, {payload=}")

    # Call the function for that specific feed
    await feeds[topic](payload.decode("utf8"))


def on_disconnect(client, packet, exc=None):
    print("Disconnected")


def on_subscribe(client, mid, qos, properties):
    for sub in client.subscriptions:
        print(f"SUBSCRIBED {sub.topic}, {sub.acknowledged=}")


async def treatbot_cam(value):
    enabled = bool(int(value))
    global treatbot_active

    source_name = Sources.treatbot_cam_source
    scene_name = Sources.treatbot_cam_scene

    obs_client.call(requests.SetSceneItemRender(enabled, source_name, scene_name))

    if enabled:
        treatbot_active = True
        await asyncio.sleep(Settings.treatbot_timeout)
        if treatbot_active:
            print(
                "Hrm.... the treatbot didn't disable the OBS display. Disabling it..."
            )
            obs_client.call(requests.SetSceneItemRender(False, source_name, scene_name))
    else:
        treatbot_active = False


async def yay(value):
    enable = bool(int(value))
    global yay_active

    source_name = Sources.yay_source
    scene_name = Sources.yay_scene

    if enable:
        if not yay_active:
            # Don't let it run again while already active
            yay_active = True

            # Turn on the Yay source
            obs_client.call(requests.SetSceneItemRender(True, source_name, scene_name))

            # Let it play
            await asyncio.sleep(5)

            # Turn it back off
            obs_client.call(requests.SetSceneItemRender(False, source_name, scene_name))

            # Reset the toggle - Has no effect on the bot, but shows correctly in the server
            mqtt_client.publish("stream/yay-toggle", "0")

            # Sleep for 45 seconds to prevent continuious abuse
            await asyncio.sleep(45)

            yay_active = False


async def follow(follower):
    source = "NewFollowScene"
    text_box = "Follower"
    scene = "Common"
    step = 40

    # Turn the source off, just in case it was left on.
    obs_client.call(requests.SetSceneItemRender(False, source, scene_name=scene))

    # Set the follower text
    obs_client.call(requests.SetTextFreetype2Properties(text_box, text=follower))

    await slide_in_from_right(source, scene, step, -1)

    # Turn the source back off
    obs_client.call(requests.SetSceneItemRender(False, source, scene_name=scene))


async def slide_in_from_right(source: str, scene: str, step: int, height: int):
    """Slides a OBS Source in from the right side of the display

    Args:
        source (str): Source Name
        scene (str): Scene Name
        step (int): How many steps per iteration to move in
        height (int): Height from the top down, -1 will set it at the bottom.
    """

    # Grab screen output values
    screen_properties = obs_client.call(requests.GetVideoInfo()).datain

    # Values of the source
    item_properties = obs_client.call(
        requests.GetSceneItemProperties(source, scene_name=scene)
    ).datain

    # Set Starting position to bottom if -1
    if height == -1:
        height = int(screen_properties["baseHeight"] - item_properties["height"]) - 10

    # Send the height, and set off right side of screen
    obs_client.call(
        requests.SetSceneItemPosition(
            source,
            height,
            screen_properties["baseWidth"] + 1,
        )
    )

    # Save how far in to slide
    slide_in_to_x = int(screen_properties["baseWidth"] - item_properties["width"])

    # Turn on the scene
    obs_client.call(requests.SetSceneItemRender(True, source, scene_name=scene))

    # Slide In
    r_from = int(screen_properties["baseWidth"])
    for x in range(r_from, slide_in_to_x, step * -1):
        obs_client.call(
            requests.SetSceneItemPosition(source, height, x, scene_name=scene)
        )

    # Move to width of item
    obs_client.call(
        requests.SetSceneItemPosition(
            source,
            height,
            slide_in_to_x,
        )
    )

    # Hold the position for a beat
    await asyncio.sleep(2)

    # Slide back out
    for x in range(
        slide_in_to_x,
        int(screen_properties["baseWidth"]) + 2,
        step * 2,
    ):
        obs_client.call(
            requests.SetSceneItemPosition(source, height, x, scene_name=scene)
        )


async def slide_in_from_left(source: str, scene: str, step: int, height: int):
    """Slides a OBS Source in from the left side of the display

    Args:
        source (str): Source Name
        scene (str): Scene Name
        step (int): How many steps per iteration to move in
        height (int): Height from the top down, -1 will set it at the bottom.
    """

    # Grab screen output values
    screen_properties = obs_client.call(requests.GetVideoInfo()).datain

    # Values of the source
    item_properties = obs_client.call(
        requests.GetSceneItemProperties(source, scene_name=scene)
    ).datain

    # Set Starting position to bottom if -1
    if height == -1:
        height = int(screen_properties["baseHeight"] - item_properties["height"]) - 10

    # Send the height, and set off left side of screen
    width = (item_properties["width"] * -1) - 1
    obs_client.call(requests.SetSceneItemPosition(source, height, width))

    # Save how far in to slide
    slide_in_to_x = 1  # Left edge sliding in to left edge of screen

    # Turn on the scene
    obs_client.call(requests.SetSceneItemRender(True, source, scene_name=scene))

    # Slide In
    r_from = -1 - int(item_properties["width"])
    for width in range(r_from, slide_in_to_x, step):
        obs_client.call(
            requests.SetSceneItemPosition(source, height, width, scene_name=scene)
        )

    # Move to width of item
    obs_client.call(
        requests.SetSceneItemPosition(
            source,
            height,
            slide_in_to_x,
        )
    )

    # Hold the position for a beat
    await asyncio.sleep(2)

    # Slide back out
    for width in range(
        slide_in_to_x,
        r_from,
        step * -2,
    ):
        obs_client.call(
            requests.SetSceneItemPosition(source, height, width, scene_name=scene)
        )


def ask_exit(*args):
    STOP.set()
    obs_client.disconnect()


async def main(client):

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_subscribe = on_subscribe

    mqtt_client.set_auth_credentials(secrets.mqtt_user, secrets.mqtt_key)
    await mqtt_client.connect(secrets.mqtt_server, secrets.mqtt_port, ssl=True)

    await STOP.wait()
    await mqtt_client.disconnect()


if __name__ == "__main__":
    feeds = {
        "stream/dispense-treat-toggle": treatbot_cam,
        "stream/yay-toggle": yay,
        # "follow": follow,
    }

    STOP = asyncio.Event()

    treatbot_active = False  # Used for automatic timeout of the treatbot camera source
    yay_active = False  # Used to keep the script from running a second time while the display is active

    loop = asyncio.get_event_loop()

    loop.add_signal_handler(signal.SIGINT, ask_exit)
    loop.add_signal_handler(signal.SIGTERM, ask_exit)

    obs_client = get_obs_client()
    mqtt_client = MQTTClient("client-id")

    loop.run_until_complete(main(mqtt_client))
