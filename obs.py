from secrets import Secrets as secrets

from Adafruit_IO import MQTTClient
from obswebsocket import obsws
from obswebsocket import requests

obs_client = obsws(secrets.obs_ip, secrets.obs_ws_port, secrets.obs_secret)
obs_client.connect()


def connected(client):
    # print("Connected to Adafruit IO.")
    for feed in feeds.keys():
        client.subscribe(feed)


def disconnected(client):
    print("BYEEEEE!!")


def subscribe(client, userdata, mid, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to feed")


def message(client, feed_id, payload):
    print(f"Feed {feed_id} received new value: {payload}")
    feeds[feed_id](payload)


def treatbot_cam(payload):
    enabled = bool(int(payload))
    obs_client.call(requests.SetSceneItemRender("TreatBot", enabled, "Common"))


feeds = {
    "dispense-treat-toggle": treatbot_cam,
}

client = MQTTClient(secrets.aio_user, secrets.aio_key)

client.on_connect = connected
client.on_disconnect = disconnected
client.on_message = message
client.on_subscribe = subscribe
client.connect()

try:
    client.loop_blocking()

except KeyboardInterrupt:
    obs_client.disconnect()
    client.disconnect()
