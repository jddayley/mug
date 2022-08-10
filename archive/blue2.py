import asyncio
from uuid import UUID
from bluepy import btle

import asyncio
from socket import if_nameindex
from bleak import discover, BleakClient
from bleak import BleakScanner
from bluepy import btle
from uuid import UUID
import base64
from datetime import datetime
import time
import json
import paho.mqtt.client as mqttClient
UUID_BATTERY = UUID("fc540007-236c-4c94-8fa9-944a3e5353fa")
UUID_DRINK_TEMPERATURE = UUID("fc540002-236c-4c94-8fa9-944a3e5353fa")
UUID_TARGET_TEMPERATURE = UUID("fc540003-236c-4c94-8fa9-944a3e5353fa")
UUID_LIQUID_LEVEL = UUID("fc540005-236c-4c94-8fa9-944a3e5353fa")
UUID_LIQUID_STATE = UUID("fc540008-236c-4c94-8fa9-944a3e5353fa")
CONNECTED = False 
def on_connect(client, userdata, flags, code):
    """Connect completion for Paho"""
    _ = client
    _ = userdata
    _ = flags
    global CONNECTED
    if code == 0:
        print("Connected to broker")
        CONNECTED = True                #Signal connection
    else:
        print("Connection failed")
def bytes_to_little_int(data: bytearray) -> int:
    """Convert bytes to little int."""
    return int.from_bytes(data, byteorder="little", signed=False)


async def _temp_from_bytes( temp_bytes: bytearray) -> float:
    """Get temperature from bytearray and convert to fahrenheit if needed."""
    temp = float(bytes_to_little_int(temp_bytes)) * 0.01
    # if use_metric is False:
    #     # Convert to fahrenheit
    temp = (temp * 9 / 5) + 32
    return round(temp, 2)


async def find_mugs():
    devices = await BleakScanner.discover()
    #muses = []
    #devices = ['C6:0E:6F:D8:CD:FC','C1:20:6D:B1:75:OE','2DF1A2F4-9454-DD22-DFAF-A3D5B330A168','35FCEA0F-D81C-23AB-5C27-B96A5C1838AA']
   # print('found ' + str(len(devices)))
    for d in devices:
     #       print(d)
        try:
            if 'Ember' in d.name:
                print(d)
                #muses.append(d)
                client = BleakClient(d)
                await client.connect()
                #paired = await client.pair()
                battery = await client.read_gatt_char(UUID_BATTERY)
                battery_percent = float(battery[0])
                ember_battery = round(battery_percent, 2)
                on_charging_base = battery[1] == 1
                temp_bytes = await client.read_gatt_char(UUID_TARGET_TEMPERATURE)
                target_temp = await _temp_from_bytes(temp_bytes)
                temp_bytes = await client.read_gatt_char(UUID_DRINK_TEMPERATURE)
                current_temp = await _temp_from_bytes(temp_bytes)
                liquid_state_bytes = await client.read_gatt_char(UUID_LIQUID_STATE)
                liquid_state = bytes_to_little_int(liquid_state_bytes)
                liquid_level_bytes = await client.read_gatt_char(UUID_LIQUID_LEVEL)
                liquid_level = bytes_to_little_int(liquid_level_bytes)
                print("Battery: " + str(ember_battery) + " Charging: " + str(on_charging_base) 
                    + " Current: " + str(current_temp) + " Target: " + str(target_temp)
                    + " State: " + str(liquid_state) + " Level: "+ str(liquid_level)
                    )
                client = connect_mqtt()
                message = {"battery": str(ember_battery),
                "charging": + on_charging_base,
                "current": str(current_temp),
                "target": str(target_temp),
                "state": str(liquid_state),
                "level": str(liquid_level)
                }
                if d == "35FCEA0F-D81C-23AB-5C27-B96A5C1838AA":
                    print("Mug1")
                    client.publish("mug1/reading", json.dumps(message))
                if d == "2DF1A2F4-9454-DD22-DFAF-A3D5B330A168":
                    print("Mug2")
                    client.publish("mug2/reading", json.dumps(message))
                client.disconnect()
        except Exception as err: 
            print ("Could not connect: " + str(err))
            client.disconnect()
    #return muses

def connect_mqtt():
    timeId =  datetime.now().strftime("%H:%M:%S")
    clientId ="MUG_" + timeId
    print(clientId)
    client = mqttClient.Client("Mug", clientId)    #create new instance
    client.on_connect = on_connect   
    client.username_pw_set("jddayley", "java")         #attach function to callback
    client.connect("192.168.0.116", port=1883) #connect to broker
    client.loop_start()
    while not CONNECTED:
        time.sleep(5)
    return client
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(find_mugs())
