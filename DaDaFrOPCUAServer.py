import netifaces as ni
import asyncio
import asyncua
import board
from datetime import datetime
import time
from asyncua import ua, Server
from asyncua.ua import ObjectIds
import adafruit_dht

#GPIOs konfigurieren
import RPi.GPIO as GPIO

# Definition der GPIOs
sensorPIN = 4
luefterPIN = 13
ledPIN = 23
# Zählweise der Pins festlegen
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
#GPIO Eingänge festlegen
GPIO.setup(sensorPIN, GPIO.IN)

#GPIO Ausgänge festlegen
GPIO.setup(ledPIN, GPIO.OUT)

GPIO.setup(luefterPIN, GPIO.OUT)
GPIO.output(luefterPIN, GPIO.LOW)
pwm = GPIO.PWM(luefterPIN, 100)
pwm.start(100.0)

async def setFanDuty(sfdc = 0.0):
    pwm.ChangeDutyCycle(sfdc)
    return

async def main():
    server=Server()
    await server.init()
    #Get the ip address opc.tcp://10.62.255.20:4840
    IPV4_Address = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
    url="opc.tcp://"+IPV4_Address+":4840"
    server.set_endpoint(url)
    
    server.set_security_policy(
     [
     ua.SecurityPolicyType.NoSecurity
     ])
    
    #OPCUA Namensraum festleben
    name="OPCUA_Musterplatine"
    addspace=await server.register_namespace(name)
    
    dev = await server.nodes.base_object_type.add_object_type(addspace, "FBS-Platine")
    await (await dev.add_variable(addspace, "sensor", 1.0)).set_modelling_rule(True)
    await (await dev.add_variable(addspace, "luefter", 0)).set_modelling_rule(True)
    await (await dev.add_variable(addspace, "Time", datetime.utcnow())).set_modelling_rule(True)
    
    # First a folder to organise our nodes
    myfolder = await server.nodes.objects.add_folder(addspace, "Raspi")
    
    # instanciate one instance of our device
    mydevice = await myfolder.add_object(addspace, "FBS-Platine", dev)
    
    # get proxy to child-elements
    sensor = await mydevice.get_child(
    [f"{addspace}:sensor"]
    )
    luefter = await mydevice.get_child(
    [f"{addspace}:luefter"]
    )
    Time = await mydevice.get_child(
    [f"{addspace}:Time"]
    )
     
    await luefter.set_writable()
    
    # Device für Sensor
    # Initial the dht device, with data pin connected to:
    dhtDevice = adafruit_dht.DHT22(board.D4, use_pulseio=False)
     #OPCUA-Server starten
    async with server:
        print("Server startet auf {}",format(url))
        
        while True:
            currentTime = datetime.now()
            await Time.set_value(currentTime)
            # Temperatur messen
            try:
                # Print the values to Console
                sensor1 = dhtDevice.temperature

                await sensor.set_value(sensor1)
                
                luefter1 = await luefter.get_value()
                if luefter1 != 0:
                    # physikalischen Lüfter anschalten
                    await setFanDuty(luefter1)
                    ## LED anschalten
                    GPIO.output(ledPIN,GPIO.HIGH)
                else:
                    # physikalischen Lüfter anschalten
                    await setFanDuty()
                    ## LED anschalten	
                    GPIO.output(ledPIN,GPIO.LOW)
                await asyncio.sleep(2.0)
                
     
            except RuntimeError as error:
                # Errors happen fairly often, DHT's are hard to read, just keep going
                print(f"{currentTime}:{error.args[0]}")
                await asyncio.sleep(2.0)
                continue
            
            
        
        

if __name__ == "__main__":
    asyncio.run(main())
