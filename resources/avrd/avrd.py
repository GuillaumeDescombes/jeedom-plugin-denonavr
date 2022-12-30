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
from typing import Any, List, Mapping, Optional, Union
from inspect import signature
from enum import Enum

try:
    from jeedom.jeedom import *
except ImportError:
    logging.error("Error: importing module from jeedom folder")
    sys.exit(1)

#
# Simple device control
class devices:
    """ A simple class with a register and unregister methods
    """

    def __init__(self, cycle:float, debug:bool):
        self.devices = {}
        self.deviceTasks = {}
        self.debug = debug
        self.notifyCmd = None
        self.notifyEvent = None
        self.shutDown = False
        self.cycle = cycle

    def register(self, info):
        if "serial" in info and "name" in info and ("ip" in info or "host" in info):
            serial = info["serial"].lower()
            name = info["name"]
            if "host" in info:
                host = info["host"]
            else:
                host = info["ip"]
            if serial not in self.deviceTasks:
                logging.info(f"Registering '{name}' ({serial}) - '{host}' in task list")
                jeedomCom.add_changes(f"devices::{serial}::{avrEnums.Zone.UndefinedZone.value}::event", {'avrName': name, 'avrSerial': serial, 'value' : 'register'});
                self.deviceTasks[serial] = aio.create_task(self.setDevice(serial, name, host))
            
    def unregister(self, serial:str):
        serial=serial.lower()
        if serial in self.deviceTasks:
            logging.info(f"Unregistering 'Unknwon' ({serial}) in task list")
            name="Unknown"
            if serial in self.devices:
              name = self.devices[serial].name
              logging.debug("'%s' is gone" % name)
              self.devices[serial].close()
              del self.devices[serial]      
            #cancel task
            self.deviceTasks[serial].cancel()            
            del self.deviceTasks[serial]
            #send event to jeedom
            jeedomCom.add_changes(f"devices::{serial}::{avrEnums.Zone.UndefinedZone.value}::event", {'avrName': name, 'avrSerial': serial, 'value' : 'unregister'});
        
    def unregisterAll(self):
        for serial in self.devicesTasks:
            self.unregister(serial)
            
    def doAction(self, serial:str, action:str, zone:avrEnums.Zone, value: Any):
        serial=serial.lower()
        if serial in self.devices:
            logging.info(f"Executing '{action}' for device '{serial}' and zone '{zone.value}'")
            device = self.devices[serial]
            try:
                func = getattr(device, f"do{action}")
                sig = signature(func)
                params = sig.parameters
                logging.debug("found a function with signature '"+str(sig)+"'")
                if "zone" in params and "value" in params and len(params) == 2:
                    logging.info(f"--> {action}({zone.value}, {value})")
                    func(zone=zone, value=value)
                elif "zone" in params and len(params) == 1:
                    logging.info(f"--> {action}({zone.value})")
                    func(zone)
                elif "value" in params and len(params) == 1:
                    logging.info(f"--> {action}({value})")
                    func(value)
                elif len(params) == 0:
                    logging.info(f"--> {action}()")
                    func()
                else:
                    logging.info(f"--> function {action} not found")
            except AttributeError as e:
                logging.info(f"function do{action} does not exist")
                
            
    def notificationCmd(self, AVR, commandDef, value):
        if isinstance(value, Enum):
            valueConv=value.value
        elif isinstance(value, List):
            valueConv=[x.value for x in value]
        elif isinstance(value, Mapping):
            valueConv={x.value:value[x] for x in value}
        else:
            valueConv=value

        if commandDef.zone != avrEnums.Zone.UndefinedZone:
            logging.debug(f"notificationCmd -> {AVR.name}: Value for '{commandDef.label}' ({commandDef.code}) in zone '{commandDef.zone.value}' changed to '{valueConv}'")
            jeedomCom.add_changes(f"devices::{AVR.serial}::{commandDef.zone.value}::{commandDef.code}", {'avrName': AVR.name, 'avrSerial': AVR.serial, 'cmdCode': commandDef.code, 'cmdLabel': commandDef.label, 'zone': commandDef.zone.value, 'value': valueConv});
        else:  
            logging.debug(f"notificationCmd -> {AVR.name}: Value for '{commandDef.label}' ({commandDef.code}) changed to '{valueConv}'")
            jeedomCom.add_changes(f"devices::{AVR.serial}::{commandDef.zone.value}::{commandDef.code}", {'avrName': AVR.name, 'avrSerial': AVR.serial, 'cmdCode': commandDef.code, 'cmdLabel': commandDef.label, 'value': valueConv});

    def notificationEvent(self, AVR, event, value):
        logging.debug(f"notificationEvent -> {AVR.name}: Event '{event.value}'")
        jeedomCom.add_changes(f"devices::{AVR.serial}::{avrEnums.Zone.UndefinedZone.value}::event", {'avrName': AVR.name, 'avrSerial': AVR.serial, 'value' : event.value});
            
    async def setDevice(self, serial: str, name: str, host:str):
        while not self.shutDown:
            if serial in self.deviceTasks:
                if serial in self.devices and self.devices[serial].alive:
                    ## all right; device is alive
                    logging.debug(f"Device '{name}' ({serial}) - '{host}' is alive")
                else:
                    logging.debug(f"Try to add '{name}' ({serial}) - '{host}' in device list")
                    try:
                        newdev = await avr.avr_factory(name, serial, host)
                        if newdev:
                            self.devices[serial] = newdev
                            self.devices[serial].notifyme(self.notificationCmd, self.notificationEvent)
                            logging.debug(f"Device '{name}' ({serial}) added in device list")
                        else:
                            logging.info(f"Could not connect to '{name}' ({serial}) - '{host}'. Try again in {self.cycle}s.")
                    except aio.CancelledError as e:
                        logging.debug(f"Task has been cancelled. Stopping task.")
                        return
                    except avr.AvrTimeoutError as e:
                        logging.debug(f"Could not connect to '{name}' ({serial}) - '{host}': TimeOut. Try again in {self.cycle}s.")
                        pass
                    except Exception as e:
                        logging.info(f"Could not connect to '{name}' ({serial}) - '{host}': {e.__class__.__name__}. Try again in {self.cycle}s.")
                        logging.debug(traceback.format_exc())    
            else:
                logging.debug(f"Device {info} has been unregistered. Stopping task.")
                return
            try:    
                await aio.sleep(self.cycle)
            except aio.CancelledError as e:
                logging.debug(f"Task has been cancelled. Stopping task.")
                return    
            
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
    
    #jeedomCom.add_changes("daemon", {'event' : 'Shutdown'})
    jeedomCom.send_change_immediate({"daemon": {'event' : 'Shutdown'}})
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
    global _cycleConnect
    global _log_level
    global _watchDogTimer
    global JEEDOM_SOCKET_MESSAGE
  
    MyDevices = devices(_cycleConnect, _log_level=="debug")
  
    logging.debug("Start listening...")
    jeedomSocket.open()
    jeedomCom.send_change_immediate({"daemon": {'event' : 'Listening'}})
    #jeedomCom.add_changes("daemon", {'event' : 'Listening'})
    try:
        await aio.sleep(5)
    except aio.CancelledError as e:
        return
  
    #listInfo = {"name":"my Denon", "ip":"192.168.128.188", "serial":"1234"}
    #MyDevices.register(listInfo)
  
    cpt=0
    while True:
        try:
            await aio.sleep(_cycle)
        except aio.CancelledError as e:
            return            
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
                    # Register/Unregister
                    if message['action'] == "register":
                        newDeviceInfo = {"name":message['name'], "ip":message['ip'], "serial":message['serial']}
                        MyDevices.register(newDeviceInfo)
                    if message['action'] == "unregister":
                        MyDevices.unregister(message['serial'])
                    if message['action'] == "unregisterAll":
                        MyDevices.unregisterAll() 
                    # action to device
                    if message['action'] == "doDevice":
                        serial = message['serial']
                        deviceAction = message['deviceAction']
                        zone = avrEnums.Zone.UndefinedZone
                        if 'zone' in message:
                            if message['zone'] == "main" or message['zone'] ==1:
                                zone = avrEnums.Zone.MainZone
                            if message['zone'] == "2" or message['zone'] ==2:
                                zone = avrEnums.Zone.Zone2    
                            if message['zone'] == "3" or message['zone'] ==3:
                                zone = avrEnums.Zone.Zone3
                        value=None
                        if 'value' in message:
                            value=message['value']
                        MyDevices.doAction(serial, deviceAction, zone, value)
                    
        except aio.CancelledError as e:
            return            
        except Exception as e:
            logging.error('Fatal error: '+str(e))
            logging.info(traceback.format_exc())
        if (_watchDogTimer > 0 and cpt % round(_watchDogTimer / _cycle) == 0):
            jeedomCom.add_changes("daemon", {'event' : 'Ping'});
            #logging.debug("Still alive")
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
_cycleConnect = 60
_watchDogTimer = 300 # 5min

parser = argparse.ArgumentParser(description='AVR Daemon for Jeedom plugin')
parser.add_argument("--sockethost", help="Socket host for server", type=str)
parser.add_argument("--socketport", help="Socket port for server", type=str)
parser.add_argument("--loglevel", help="Log Level for the daemon", type=str)
parser.add_argument("--callback", help="Callback", type=str)
parser.add_argument("--apikey", help="Apikey", type=str)
parser.add_argument("--cycle", help="Cycle to send event", type=str)
parser.add_argument("--cycleConnect", help="Cycle to connect to device", type=str)
parser.add_argument("--watchDogTimer", help="watch dog time", type=str)
parser.add_argument("--pid", help="Pid file", type=str)
args = parser.parse_args()

if args.sockethost:
    _socket_host = args.sockethost
if args.socketport:
    _socket_port = int(args.socketport)
#if args.loglevel:
#    _log_level = args.loglevel
if args.callback:
    _callback = args.callback
if args.apikey:
    _apikey = args.apikey
if args.pid:
    _pidfile = args.pid
if args.cycle:
    _cycle = float(args.cycle)
if args.cycleConnect:
    _cycleConnect = float(args.cycleConnect)
if args.watchDogTimer:
    _watchDogTimer = float(args.watchDogTimer)

jeedom_utils.set_log_level(_log_level)

logging.info('Start avrd')
logging.info('Log level: '+str(_log_level))
logging.info('PID file: '+str(_pidfile))
logging.info('Apikey: '+str(_apikey))
logging.info('Socket: '+str(_socket_host)+':'+str(_socket_port))
logging.info('Callback: '+str(_callback))
logging.info('Cycle: '+str(_cycle))
logging.info('CycleConnect: '+str(_cycleConnect))
logging.info('WatchdogTimer: '+str(_watchDogTimer))

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
    logging.error('Fatal error: '+str(e))
    logging.info(traceback.format_exc())
    shutdown()