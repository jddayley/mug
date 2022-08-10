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


async def find_mugs():
    devices = await BleakScanner.discover()

    #muses = []
    # devices = [
    #     'C6:0E:6F:D8:CD:FC','C1:20:6D:B1:75:0E', '2DF1A2F4-9454-DD22-DFAF-A3D5B330A168',
    #     '35FCEA0F-D81C-23AB-5C27-B96A5C1838AA'
    # ]
    # print('found ' + str(len(devices)))

    
  #  for _ in range(150):
    for d in devices:
        print(d)
        try:
            if 'Ember' in d.name:
                print(d.address)
                #muses.append(d)
                async with BleakClient(d.address, timeout=20.0, use_cached=False) as client:
                    #pair = await client.pair()
                    print(f"Connected: {client.is_connected}")
                    await client.start_notify(
                       UUID_PUSH_EVENT, partial(push_notify, client)
                    )
                    #await client.start_notify(UUID_PUSH_EVENT, push_notify,client)
                    print("subscribe to notifications")
                    svcs = await client.get_services()
                    print("Services:")
                    for service in svcs:
                        print(service)  #paired = await client.pair()
                    ember_battery, on_charging_base, target_temp, current_temp, liquid_state, liquid_level = await get_state(client)

                    mq_publish(d.address, ember_battery, on_charging_base, target_temp, current_temp, liquid_state, liquid_level)
                    #client.disconnect()
                    while True:
                        await asyncio.sleep(1.0)
        except Exception as err:
            print("Dons - Could not connect: " + str(err))
    await asyncio.sleep(10) 

async def get_state(client):
    battery = await client.read_gatt_char(UUID_BATTERY)
    battery_percent = float(battery[0])
    ember_battery = round(battery_percent, 2)
    on_charging_base = battery[1] == 1
    temp_bytes = await client.read_gatt_char(
                        UUID_TARGET_TEMPERATURE)
    target_temp = await _temp_from_bytes(temp_bytes)
    temp_bytes = await client.read_gatt_char(
                        UUID_DRINK_TEMPERATURE)
    current_temp = await _temp_from_bytes(temp_bytes)
    liquid_state_bytes = await client.read_gatt_char(
                        UUID_LIQUID_STATE)
    liquid_state = bytes_to_little_int(liquid_state_bytes)
    liquid_level_bytes = await client.read_gatt_char(
                        UUID_LIQUID_LEVEL)
    liquid_level = bytes_to_little_int(liquid_level_bytes)
    print("Battery: " + str(ember_battery) + " Charging: " +
                        str(on_charging_base) + " Current: " +
                        str(current_temp) + " Target: " + str(target_temp) +
                        " State: " + str(liquid_state) + " Level: " +
                        str(liquid_level))
        
    return ember_battery,on_charging_base,target_temp,current_temp,liquid_state,liquid_level

def mq_publish(client: BleakClient, ember_battery, on_charging_base, target_temp, current_temp, liquid_state, liquid_level):
    mqclient = connect_mqtt()
    message = {
                        "battery": str(ember_battery),
                        "charging": + on_charging_base,
                        "current": str(current_temp),
                        "target": str(target_temp),
                        "state": str(liquid_state),
                        "level": str(liquid_level)
                    }
    print(client.address)
    if client.address == "35FCEA0F-D81C-23AB-5C27-B96A5C1838AA" or client.address == "C1:20:6D:B1:75:0E" :
        print("Mug1")
        resp = mqclient.publish("mug1/reading",
                                json.dumps(message))
        print("Published: " + str(resp))
    if client.address == "2DF1A2F4-9454-DD22-DFAF-A3D5B330A168" or client.address == "C6:0E:6F:D8:CD:FC"  :
        print("Mug2")
        resp = mqclient.publish("mug2/reading",
                                json.dumps(message))
        print("Published: " + str(resp))
    resp = mqclient.publish(client.address + "/reading",json.dumps(message))
    print("Published: " + str(resp))
def connect_mqtt():
    timeId = datetime.now().strftime("%H:%M:%S")
    clientId = "MUG_" + timeId
    print(clientId)
    client = mqttClient.Client("Mug", clientId)  #create new instance
    client.on_connect = on_connect
    client.username_pw_set("jddayley", "java")  #attach function to callback
    client.connect("192.168.0.116", port=1883)  #connect to broker
    client.loop_start()
    while not CONNECTED:
        time.sleep(5)
    return client
    
async def push_notify(client: BleakClient, sender: int, data: bytearray):
    print("Push events from the mug to indicate changes.")
    try:
        ember_battery, on_charging_base, target_temp, current_temp, liquid_state, liquid_level = await get_state(client)
        mq_publish(client, ember_battery, on_charging_base, target_temp, current_temp, liquid_state, liquid_level)
        print("Notification changes complete")
    except Exception as err:
        print("Dons - Could not connect: " + str(err))            


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(find_mugs())
    


