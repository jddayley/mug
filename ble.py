import asyncio
from functools import partial
from socket import if_nameindex
from bleak import discover, BleakClient, BleakError
from bleak import BleakScanner
from uuid import UUID
import base64
from datetime import datetime
import time
import json
from const import *
import inspect
import paho.mqtt.client as mqttClient


def on_connect(client, userdata, flags, code):
    """Connect completion for Paho"""
    _ = client
    _ = userdata
    _ = flags
    global CONNECTED
    if code == 0:
        print("Connected to broker")
        CONNECTED = True  #Signal connection
    else:
        print("Connection failed")


def bytes_to_little_int(data: bytearray) -> int:
    """Convert bytes to little int."""
    return int.from_bytes(data, byteorder="little", signed=False)


async def _temp_from_bytes(temp_bytes: bytearray) -> float:
    """Get temperature from bytearray and convert to fahrenheit if needed."""
    temp = float(bytes_to_little_int(temp_bytes)) * 0.01
    # if use_metric is False:
    #     # Convert to fahrenheit
    temp = (temp * 9 / 5) + 32
    return round(temp, 2)


async def find_mugs(address):
    print("Connecting to : " + str(address))
    try:

        print(address)
        async with BleakClient(address, timeout=20.0,
                               use_cached=False) as client:
            #async with BleakClient(address) as client:
            #pair = await client.pair()
            print(f"Connected: {client.is_connected}")
            await client.start_notify(UUID_PUSH_EVENT,
                                      partial(push_notify, client, address))
            print("subscribe to notifications")
            svcs = await client.get_services()
            print("Services:")
            for service in svcs:
                print(service)
            ember_battery, on_charging_base, target_temp, current_temp, liquid_state, liquid_level = await get_state(
                client)

            mq_publish(address, ember_battery, on_charging_base, target_temp,
                       current_temp, liquid_state, liquid_level)
            await asyncio.sleep(60.0)
            await client.stop_notify(UUID_PUSH_EVENT)

    except Exception as err:
        print("Dons - Could not connect: " + str(err))


async def get_state(client):
    battery = await client.read_gatt_char(UUID_BATTERY)
    battery_percent = float(battery[0])
    ember_battery = round(battery_percent, 2)
    on_charging_base = battery[1] == 1
    temp_bytes = await client.read_gatt_char(UUID_TARGET_TEMPERATURE)
    target_temp = await _temp_from_bytes(temp_bytes)
    temp_bytes = await client.read_gatt_char(UUID_DRINK_TEMPERATURE)
    current_temp = await _temp_from_bytes(temp_bytes)
    liquid_state_bytes = await client.read_gatt_char(UUID_LIQUID_STATE)
    liquid_state_int = bytes_to_little_int(liquid_state_bytes)
    liquid_state = "Unknown"
    if (liquid_state_int == 0):
        liquid_state = "Unknown"
    elif (liquid_state_int == 1):
        liquid_state = "Empty"
    elif (liquid_state_int == 2):
        liquid_state = "Filling"
    elif (liquid_state_int == 3):
        liquid_state = "Cold (No control)"
    elif (liquid_state_int == 4):
        liquid_state = "Cooling"
    elif (liquid_state_int == 5):
        liquid_state = "Heating"
    elif (liquid_state_int == 6):
        liquid_state = "Perfect"
    elif (liquid_state_int == 7):
        liquid_state = "Warm (No control)"

    liquid_level_bytes = await client.read_gatt_char(UUID_LIQUID_LEVEL)
    liquid_level_int = bytes_to_little_int(liquid_level_bytes)
    liquid_level = round(liquid_level_int / 30 * 100, 2)
    print("Battery: " + str(ember_battery) + " Charging: " +
          str(on_charging_base) + " Current: " + str(current_temp) +
          " Target: " + str(target_temp) + " State: " + str(liquid_state) +
          " Level: " + str(liquid_level))

    return ember_battery, on_charging_base, target_temp, current_temp, liquid_state, liquid_level


def mq_publish(address, ember_battery, on_charging_base, target_temp,
               current_temp, liquid_state, liquid_level):
    mqclient = connect_mqtt()
    message = {
        "battery": str(ember_battery),
        "charging": +on_charging_base,
        "current": str(current_temp),
        "target": str(target_temp),
        "state": str(liquid_state),
        "level": str(liquid_level)
    }
    print(address)
    if address == "35FCEA0F-D81C-23AB-5C27-B96A5C1838AA" or address == "C1:20:6D:B1:75:0E":
        print("Mug1")
        resp = mqclient.publish("mug1/reading", json.dumps(message))
        print("Published: " + str(resp))
    if address == "2DF1A2F4-9454-DD22-DFAF-A3D5B330A168" or address == "C6:0E:6F:D8:CD:FC":
        print("Mug2")
        resp = mqclient.publish("mug2/reading", json.dumps(message))
        print("Published: " + str(resp))


def connect_mqtt():
    timeId = datetime.now().strftime("%H:%M:%S")
    clientId = "MUG_" + timeId
    print(clientId)
    client = mqttClient.Client("Mug_Mac_1", clientId)  #create new instance
    client.on_connect = on_connect
    client.username_pw_set("jddayley", "java")  #attach function to callback
    client.connect("192.168.0.116", port=1883)  #connect to broker
    client.loop_start()
    while not CONNECTED:
        time.sleep(5)
    return client


async def push_notify(client: BleakClient, address, sender: int,
                      data: bytearray):
    print("Push events from the mug to indicate changes.")
    try:
        ember_battery, on_charging_base, target_temp, current_temp, liquid_state, liquid_level = await get_state(
            client)
        mq_publish(address, ember_battery, on_charging_base, target_temp,
                   current_temp, liquid_state, liquid_level)
        print("Notification changes complete")
    except Exception as err:
        print("Dons - Could not connect: " + str(err))


async def main(addresses):
    fun1 = find_mugs("C1:20:6D:B1:75:0E")
    fun2 = find_mugs("C6:0E:6F:D8:CD:FC")
    #fun3 = find_mugs("2DF1A2F4-9454-DD22-DFAF-A3D5B330A168")
    #fun4 = find_mugs("35FCEA0F-D81C-23AB-5C27-B96A5C1838AA")
    print(type(find_mugs))
    print(inspect.iscoroutinefunction(find_mugs))
    print(inspect.iscoroutine(fun1))
    #asyncio.gather(fun1, fun2, fun3, fun4)
    asyncio.gather(fun1, fun2)
    await asyncio.sleep(60.0)


if __name__ == '__main__':
    asyncio.run(
        main([
            "C1:20:6D:B1:75:0E",
            "C6:0E:6F:D8:CD:FC",
            "2DF1A2F4-9454-DD22-DFAF-A3D5B330A168",
            "35FCEA0F-D81C-23AB-5C27-B96A5C1838AA",
        ]))
