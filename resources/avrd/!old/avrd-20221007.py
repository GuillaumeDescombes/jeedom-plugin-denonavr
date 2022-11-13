# This file is part of Jeedom.
#
# Jeedom is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Jeedom is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Jeedom. If not, see <http://www.gnu.org/licenses/>.

import string
import sys
import os
import time
import datetime
import argparse
import binascii
import re
import signal
import traceback
from optparse import OptionParser
from os.path import join
import json
import aiomadeavr as avr
import aiomadeavr.enums as avrEnums
import asyncio as aio
import logging
import aiohttp
from xml.dom.minidom import parseString


#try:
from jeedom.jeedom import *
#except ImportError:
#    logging.error("Error: importing module from jeedom folder")
#    sys.exit(1)

#
# Simple device control
class devices:
    """ A simple class with a register and unregister methods
    """

    def __init__(self, debug):
        self.devices = {}
        self.deviceTasks = {}
        self.doi = None  # device of interest
        self.secondary = None  # Either "source", "surround", or channel
        self.debug = debug
        self.notifyCmd = None
        self.notifyEvent = None
        self.shutDown = False

    def register(self, info):
        logging.debug(f"Registering '{info['name']}'")
        if "serial" in info and info["serial"].lower() not in self.deviceTasks:
            jeedomCom.add_changes("devices::"+info["serial"].lower()+"::"+avrEnums.Zone.UndefinedZone.value+"::event", {'avrName': info["name"], 'avrSerial': info["serial"].lower(), 'value' : 'register'});
            self.deviceTasks[info["serial"].lower()] = aio.create_task(self.setDevice(info))
            
    async def registerByAddr(self, addr):
        try:
            rdata = await self.getInfo(addr)
            jeedomCom.add_changes("infos::"+addr, rdata);
            info = {"name":rdata["name"] , "ip":addr, "serial":rdata["serial"]}
            self.register(info)
        except Exception as e:
            logging.error(f"Cannot get info and register {addr}")

    def unregister(self, serial):
        if serial.lower() in self.deviceTasks:
            logging.debug(f"Unregistering '{serial.lower()}'")
            if serial.lower() in self.devices:
              logging.debug("'%s' is gone" % self.devices[serial.lower()].name)
              self.devices[serial.lower()].close()
              del self.devices[serial.lower()]
              
            #cancel task
            self.deviceTasks[serial.lower()].cancel()            
            del self.deviceTasks[serial.lower()]
            
    def notificationCmd(self, AVR, commandDef, value):
        if commandDef.zone != avrEnums.Zone.UndefinedZone:
            print("-> {}: Value for '{}' ({}) in zone '{}' changed to '{}'".format(AVR.name, commandDef.label, commandDef.code, commandDef.zone.value, value))
            jeedomCom.add_changes("devices::"+AVR.serial+"::"+commandDef.zone.value+"::"+commandDef.code, {'avrName': AVR.name, 'avrSerial': AVR.serial, 'cmdCode': commandDef.code, 'cmdLabel': commandDef.label, 'zone': commandDef.zone.value, 'value': value});
        else:  
            print("-> {}: Value for '{}' ({}) changed to '{}'".format(AVR.name, commandDef.label, commandDef.code, value))
            jeedomCom.add_changes("devices::"+AVR.serial+"::"+commandDef.zone.value+"::"+commandDef.code, {'avrName': AVR.name, 'avrSerial': AVR.serial, 'cmdCode': commandDef.code, 'cmdLabel': commandDef.label, 'value': value});

    def notificationEvent(self, AVR, event, value):
        print("-> {}: Event '{}'".format(AVR.name, event.value))
        jeedomCom.add_changes("devices::"+AVR.serial+"::"+avrEnums.Zone.UndefinedZone.value+"::event", {'avrName': AVR.name, 'avrSerial': AVR.serial, 'value' : event.value});
            
    async def setDevice(self, info):
        while not self.shutDown:
            if info["serial"].lower() in self.deviceTasks:
                if info["serial"].lower() in self.devices and self.devices[info["serial"].lower()].alive:
                    ## all right; device is alive
                    logging.debug(f"Device '{info['name']}' is alive")
                else:
                    logging.debug(f"Try to add '{info['name']}' ({info['serial'].lower()}) in device list")
                    try:
                        newdev = await avr.avr_factory(info["name"], info["serial"].lower(), info["ip"])
                        if newdev:
                            self.devices[info["serial"].lower()] = newdev
                            self.devices[info["serial"].lower()].notifyme(self.notificationCmd, self.notificationEvent)
                            logging.debug(f"Device '{info['name']}' added in device list")
                        else:
                            logging.warning("Could not connect to {}. Try again in 60s.".format(info['ip']))
                    except aio.CancelledError as e:
                        return
                    except Exception as e:
                        logging.warning("Could not connect to {}: {}. Try again in 60s.".format(info['ip'], e.__class__.__name__))
            else:
                logging.debug(f"Device {info} has been unregistered. Cancelling task.")
                return
            await aio.sleep(60)
            
    async def getInfo(self, addr):
        def getText(nodelist):
            rc = []
            for node in nodelist:
                if node.nodeType == node.TEXT_NODE:
                    rc.append(node.data)
            return "".join(rc)
        
        rdata = None
        try:
            txt = None
            #http://192.168.128.188:60006/upnp/desc/aios_device/aios_device.xml
            url = "http://" + addr + ":60006/upnp/desc/aios_device/aios_device.xml"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    txt = await response.text()
            if txt:
                data = parseString(txt)
                if data.getElementsByTagName("device"):
                    dev = data.getElementsByTagName("device")[0]
                    rdata = {"addr": addr}
                    if dev.getElementsByTagName("manufacturer"):
                        rdata["brand"] = getText(
                            dev.getElementsByTagName("manufacturer")[0].childNodes
                        )
                    if dev.getElementsByTagName("modelName"):
                        rdata["model"] = getText(
                            dev.getElementsByTagName("modelName")[0].childNodes
                        )
                    if dev.getElementsByTagName("serialNumber"):
                        rdata["serial"] = getText(
                            dev.getElementsByTagName("serialNumber")[0].childNodes
                        )
                    if dev.getElementsByTagName("friendlyName"):
                        rdata["name"] = getText(
                            dev.getElementsByTagName("friendlyName")[0].childNodes
                        )    
                    if dev.getElementsByTagName("deviceList"):
                        devList = dev.getElementsByTagName("deviceList")[0].getElementsByTagName("device")
                        for dev in devList:
                            if dev.getElementsByTagName("deviceType"):
                                deviceType = getText(dev.getElementsByTagName("deviceType")[0].childNodes)
                                if "ACT-Denon" in deviceType:
                                    if dev.getElementsByTagName("lanMac"):
                                        rdata["lanMac"] = getText(
                                            dev.getElementsByTagName("lanMac")[0].childNodes
                                        )                     
                                    if dev.getElementsByTagName("wlanMac"):
                                        rdata["wlanMac"] = getText(
                                            dev.getElementsByTagName("wlanMac")[0].childNodes
                                        )
                logging.debug(f"Got info for device {addr}: {rdata}")
                return rdata
        except Exception as e:
            logging.error(f"Error: Error when parsing location XML: {e}")            
            

    def stop(self):
        for dev in self.devices.values():
            dev.close()
        self.shutDown=True    
##


def handler(signum=None, frame=None):
    logging.info("Signal %i caught, exiting..." % int(signum))
    shutdown()
    
def shutdown():
    global MyDevices
    global jeedomSocket
    
    jeedomCom.add_changes("daemon", {'event' : 'Shutdown'});
    logging.info("Shutdown")
    try:
        if MyDevices:
            MyDevices.stop()
    except:
        pass
        
    logging.info("Removing PID file " + str(_pidfile))
    try:
        os.remove(_pidfile)
    except:
        pass
    logging.info("Closing jeedom Socket ")        
    try:
        jeedomSocket.close()
    except:
        pass        
    logging.info("Exit 0")
    sys.stdout.flush()
    os._exit(0)
    

async def main():
  global MyDevices
  global jeedomSocket
  global jeedomCom
  global _cycle
  global JEEDOM_SOCKET_MESSAGE
  
  print("starting...")
  MyDevices = devices(True)
  
  logging.debug("Start listening...")
  jeedomSocket.open()
  jeedomCom.add_changes("daemon", {'event' : 'Listening'})
  await aio.sleep(5)
  
  #listInfo = {"name":"my Denon", "ip":"192.168.128.188", "serial":"1234"}
  #MyDevices.register(listInfo)
  await MyDevices.registerByAddr("192.168.128.188")
  
  cpt=0
  while True:
    await aio.sleep(_cycle)
    try:
        if not JEEDOM_SOCKET_MESSAGE.empty():
            logging.debug("Message received in socket JEEDOM_SOCKET_MESSAGE")
            jsonMessage=JEEDOM_SOCKET_MESSAGE.get()
            logging.debug(f"message {jsonMessage}")
            message = json.loads(jsonMessage)
            if message['apikey'] != _apikey:
                logging.error("Invalid apikey from socket : " + str(message))
            else: 
                # do the action
                if message['action'] == "registerByAddr":
                    await MyDevices.registerByAddr(message['addr'])
                if message['action'] == "unregister":
                    MyDevices.unregister(message['serial'])
                if message['action'] == "getinfo":
                    rdata = await MyDevices.getInfo(message['addr'])
                    jeedomCom.add_changes("infos::"+message['addr'], rdata);
                             
    except aio.CancelledError as e:
        return            
    except Exception as e:
        logging.error(str(e))
    if cpt % round(30 / _cycle) == 0:
        #jeedomCom.add_changes("daemon", {'event' : 'Ping'});
        print(".")
        cpt = 0
    cpt=cpt+1



# ----------------------------------------------------------------------------

jeedomSocket = None
jeedomCom=None
MyDevices = None

_log_level = "debug"
_socket_port = 55010
_socket_host = '127.0.0.1'
_pidfile = '/tmp/avrd.pid'
_apikey = 'cUrBPBf1TEud0QBLFrgCuS5kLRFHRdgxRFmcFcTHRdHDCe91mKH3IK96655919i7'
_callback = 'http://127.0.0.1:80/plugins/denonavr/core/php/jeeDenonAVR.php'
_cycle = 1

parser = argparse.ArgumentParser(description='AVR Daemon for Jeedom plugin')
parser.add_argument("--socketport", help="Socketport for server", type=str)
parser.add_argument("--loglevel", help="Log Level for the daemon", type=str)
parser.add_argument("--callback", help="Callback", type=str)
parser.add_argument("--apikey", help="Apikey", type=str)
parser.add_argument("--cycle", help="Cycle to send event", type=str)
parser.add_argument("--pid", help="Pid file", type=str)
args = parser.parse_args()

if args.loglevel:
    _log_level = args.loglevel
if args.callback:
    _callback = args.callback
if args.apikey:
    _apikey = args.apikey
if args.pid:
    _pidfile = args.pid
if args.cycle:
    _cycle = float(args.cycle)

jeedom_utils.set_log_level(_log_level)

logging.info('Start avrd')
logging.info('Log level : '+str(_log_level))
logging.info('PID file : '+str(_pidfile))
logging.info('Apikey : '+str(_apikey))
logging.info('Callback : '+str(_callback))
logging.info('Cycle : '+str(_cycle))

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

try:
    jeedom_utils.write_pid(str(_pidfile))
    jeedomCom = jeedom_com(apikey = _apikey,url = _callback,cycle=_cycle)
    if not jeedomCom.test():
        logging.error('Network communication issues. Please fix your Jeedom network configuration.')
        shutdown()
    jeedomSocket = jeedom_socket(port=_socket_port,address=_socket_host)
    aio.run(main())
    shutdown()
except Exception as e:
    logging.error('Fatal error : '+str(e))
    logging.info(traceback.format_exc())
    shutdown()