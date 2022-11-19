#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# Inspired by https://github.com/silvester747/aio_marantz_avr
#
# This is to control Denon/Marantz AVR devices
#
# Copyright (c) 2020 François Wautier
# Copyright (c) 2022 Guillaume Descombes
#
# Note large part of this code was taken from scapy and other opensource software
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
# IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

"""Control of an AVR over Telnet."""

import asyncio
import logging
import re
import time
from enum import Enum
from typing import Any, List, Mapping, Optional, Callable, Union
from .enums import *
import traceback

# Some replacement for the surround sound format
SSTRANSFORM = [
    #("Audio-", " "),
    ("Dd", "Dolby Digital "),
    ("Hd", "HD "),
    ("DD", "Dolby Digital "),
    ("Dts", "DTS"),
    ["Mstr", "Master "],
    ("Dsur", "Digital Surround "),
    ("Mtrx", "Matrix"),
    ("Dscrt", "Discrete "),
    ("Mch", "Multi-Channel "),
    (" Es ", " ES "),
]
EXTRAS = ["SSINFAISFSV"]
NEEDSPACE = ["PSDEL", "PSDYNVOL", "PSDRC", "PSLFE", "PSTRE", "Z2PSTRE", "Z3PSTRE", "PSBAS", "Z2PSBAS", "Z3PSBAS", "DA", "DASTN"]
NOTTOREFRESH = ["PSTONE", "DASTN"]
ADDTOREFRESH =["DA"]

def only_int(val: str) -> str:
    return "".join(
        [x for x in val if x in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]]
    )


class AvrError(Exception):
    """Base class for all errors returned from an AVR."""

    pass


class AvrTimeoutError(AvrError):
    """A request to the AVR has timed out."""

    pass


async def avr_factory(
    name: str, serial: str, host: str, port: int = 23, timeout: float = 3.0
) -> "MDAVR":
    """Connect to an AVR.

        :param name: The name of this device.
        :type url: str
        :param addr: The device IP address
        :type name: str
        :returns: A device instance or None if connection cannot be established
        :rtype: MDAVR
    """
    try:
        future = asyncio.open_connection(host, port=port)
        reader, writer = await asyncio.wait_for(future, timeout=timeout)
        return MDAVR(name, serial, reader, writer, timeout)
    except asyncio.TimeoutError as e:
        logging.debug("error when connecting to '{}': timeout".format(host))
        raise AvrTimeoutError("timeout")
    except Exception as e:
        logging.debug("error when connecting to {}: {}".format(host, e))
        return None

def _on_off_from_bool(value: bool) -> str:
    if value:
        return "ON"
    else:
        return "OFF"


def _on_off_to_bool(value: str) -> bool:
    return value == "ON"

def _list_enum_to_string(myList: List[Enum]) -> str:
    return "["+",".join([""+x.name+":"+x.value+"" for x in myList])+"]"

def _dict_enum_to_string(myDict: Mapping[ChannelBias, Any]) -> str:
    return "["+",".join([""+x.name+":"+x.value+" => "+str(myDict[x]) for x in myDict])+"]"


class _CommandDef:
    code: str
    label: str
    zone: Zone
    values: Optional[Enum]

    def __init__(self, code: str, label: str, zone, vals: Any):
        self.code = code
        self.label = label
        self.values = vals
        self.zone = zone
       


class MDAVR:
    """Connection to a Marantz AVR over Telnet.

    Uses `connect` to create a connection to the AVR.
    """

    CMDS_DEFS: Mapping[str, _CommandDef] = {
        "PW": _CommandDef("PW", "Main Power", Zone.UndefinedZone, Power),
        "ZM": _CommandDef("ZM", "Power", Zone.MainZone, Power),
        "Z2": _CommandDef("Z2", "Power", Zone.Zone2, Power),
        "Z3": _CommandDef("Z3", "Power", Zone.Zone3, Power),
        "MU": _CommandDef("MU", "Muted", Zone.MainZone, None),
        "Z2MU": _CommandDef("Z2MU", "Muted", Zone.Zone2, None),
        "Z3MU": _CommandDef("Z3MU", "Muted", Zone.Zone3, None),
        "MV": _CommandDef("MV", "Volume", Zone.MainZone, None),
        "Z2MV": _CommandDef("Z2MV", "Volume", Zone.Zone2, None),
        "Z3MV": _CommandDef("Z3MV", "Volume", Zone.Zone3, None),
        "SI": _CommandDef("SI", "Source", Zone.MainZone, InputSource),
        "Z2SI": _CommandDef("Z2SI", "Source", Zone.Zone2, InputSource),
        "Z3SI": _CommandDef("Z3SI", "Source", Zone.Zone3, InputSource),
        "SV": _CommandDef("SV", "Video Mode", Zone.UndefinedZone, InputSource),
        "MS": _CommandDef("MS", "Surround Mode", Zone.UndefinedZone, SurroundMode),
        "CV": _CommandDef("CV", "Channel Bias", Zone.UndefinedZone, ChannelBias),
        "PV": _CommandDef("PV", "Picture Mode", Zone.UndefinedZone, PictureMode),
        "ECO": _CommandDef("ECO", "Eco Mode", Zone.UndefinedZone, EcoMode),
        "SSSOD": _CommandDef("SSSOD", "Available Source", Zone.UndefinedZone, InputSource),
        "PSDEL": _CommandDef("PSDEL", "Sound Delay", Zone.UndefinedZone, None),
        "PSDRC": _CommandDef("PSDRC", "Dynamic Range Compression", Zone.UndefinedZone, DRCMode),
        "PSDYNVOL": _CommandDef("PSDYNVOL", "Dynamic Volume", Zone.UndefinedZone, DynamicMode),
        "PSLFE": _CommandDef("PSLFE", "Sound LFE", Zone.UndefinedZone, None),
        "PSBAS": _CommandDef("PSBAS", "Sound Bass", Zone.MainZone, None),
        "Z2PSBAS": _CommandDef("Z2PSBAS", "Sound Bass", Zone.Zone2, None),
        "Z3PSBAS": _CommandDef("Z3PSBAS", "Sound Bass", Zone.Zone3, None),
        "PSTRE": _CommandDef("PSTRE", "Sound Treble", Zone.MainZone, None),
        "Z2PSTRE": _CommandDef("Z2PSTRE", "Sound Treble", Zone.Zone2, None),
        "Z3PSTRE": _CommandDef("Z3PSTRE", "Sound Treble", Zone.Zone3, None),
        "PSTONE": _CommandDef("PSTONE", "Sound Tone Control", Zone.UndefinedZone, None),
        "DASTN": _CommandDef("DASTN", "Tuner Station Name", Zone.UndefinedZone, None),
        "TFANNAME": _CommandDef("TFANNAME", "Tuner Station Name", Zone.UndefinedZone, None),
        "TPAN": _CommandDef("TPAN", "Tuner Preset", Zone.UndefinedZone, None),
        "TMAN": _CommandDef("TMAN", "Tuner Mode", Zone.UndefinedZone, None),
        
        # To be added
        # PSCLV - Sound Center Level
        # PSRSTR - Sound Audio Restorer
        # PSDYNEQ - Sound Dyn Eq
        # PSREFLEV - Sound Dyn Eq Ref Level
        # PSHEQ - Sound Headphone EQ
        # DA -  DASTN Long Station Name
        #       DAPTY Program Type
        #       DAENL Ensemble Label
        #       DAFRQ Frequency
        #       DAQUA Quality
        #       DAINF Audio Information
        # ....
        # SSANA ? analog inputs
        # SSHDM ? Mapping between source and HDMI connection
        # SSIPM ?
        # SSDIN ? digital inputs,  COax OPtical
        # SSSPC ? Speakers' configuration
        # SSPAA ? Not sure. Active speakers config? Also returns SSSPC
        # SSQSNZMA ?  Smart select.. what for?        
        # 
    }

    _reader: asyncio.StreamReader
    _writer: asyncio.StreamWriter
    _timeout: float
    _lastMessageTime: float
    _pingFreq: float
    _timeoutCnt: float

    def __init__(
        self,
        name: str,
        serial: str,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        timeout: float = 3,
        pingFreq: float = 30
    ):
        self.name = name
        self.serial = serial
        self._reader = reader
        self._writer = writer
        self._timeout = timeout
        self._pingFreq = pingFreq
        self.status = {}
        self.maxvol = 98  # Good default ;)
        self.alive = True
        self.write_queue = asyncio.Queue()
        for cmd in self.CMDS_DEFS:
            self._clear_current(cmd)

        self.cvend = True
        self.notifyCmd = None
        self.notifyEvent = None
        self.mysources = []
        self.mysourcesNotUsed = []
        self._lastMessageTime = 0
        self._timeoutCnt = 0
        # Start reading
        self.wtask = asyncio.get_event_loop().create_task(self._do_write())
        self.rtask = asyncio.get_event_loop().create_task(self._do_read())
        self.ptask = asyncio.get_event_loop().create_task(self._do_ping())
        self._get_capabilities()
        self.doRefresh()
        if self.notifyEvent:
          self.notifyEvent(self, EventAVR.Init, {})

    def _get_capabilities(self):
        """
        Here we try to get the various capabilities of the device connected.
        """
        # Let's get the available Sources
        self.write_queue.put_nowait(("SSSOD", " ?"))

    def _get_current(self, cmd) -> Any:
        return self.status[self.CMDS_DEFS[cmd].code]
        
    def _clear_current(self, cmd):
        self.status[self.CMDS_DEFS[cmd].code]= None
        
    def _get_list(self, cmd):
        return [x for x in list(self.CMDS_DEFS[cmd].values)]
        
    # API Starts here
    @property
    def powerAVR(self) -> Optional[Power]:
        """Power state of the AVR."""
        return self._get_current("PW")

    @property
    def powerZone(self, zone: Zone) -> Optional[Power]:
        """Power state of the AVR."""
        if zone== zone.MainZone:
          return self._get_current("ZM")
        elif zone == zone.Zone2:
          return self._get_current("Z2")
        elif zone == zone.Zone3:
          return self._get_current("Z3")
        else: raise AvrError("Unknown Zone") 


    @property
    def muted(self, zone: Zone) -> Optional[bool]:
        """Boolean if volume is currently muted."""
        if zone == zone.MainZone:
          return self._get_current("MU")
        elif zone == zone.Zone2:
          return self._get_current("Z2MU")
        elif zone == zone.Zone3:
          return self._get_current("Z3MU")
        else: raise AvrError("Unknown Zone")   


    @property
    def volume(self, zone: Zone) -> Optional[float]:
        """Volume level of the AVR zone (00..max_volume)."""
        if zone == zone.MainZone:
          return self._get_current("MV")
        elif zone == zone.Zone2:
          return self._get_current("Z2MV")
        elif zone == zone.Zone3:
          return self._get_current("Z2MV")
        else: raise AvrError("Unknown Zone") 
        

    @property
    def maxVolume(self) -> Optional[float]:
        """Maximum volume level of the AVR zone."""
        return self.maxvol

    @property
    def source(self, zone: Zone) -> Optional[InputSource]:
        """Name of the current input source."""
        if zone == zone.MainZone:
          return self._get_current("SI")
        elif zone == zone.Zone2:
          return self._get_current("Z2SI")
        elif zone == zone.Zone3:
          return self._get_current("Z3SI")
        else: raise AvrError("Unknown Zone")         
        
    @property
    def sourceList(self) -> List[InputSource]:
        """List of available input sources."""
        if self.mysources:
            return self.mysources
        return self._get_list("SI")

    @property
    def sourceListNotUsed(self) -> List[InputSource]:
        """List of available input sources."""
        if self.mysourcesNotUsed:
            return self.mysourcesNotUsed
        return []

    @property
    def soundMode(self) -> Optional[SurroundMode]:
        """Name of the current sound mode."""
        return self._get_current("MS")

    @property
    def soundModeList(self) -> List[SurroundMode]:
        """List of available sound modes."""
        return self._get_list("MS")

    @property
    def pictureMode(self) -> Optional[PictureMode]:
        """Name of the current sound mode."""
        return self._get_current("PV")

    @property
    def pictureModeList(self) -> List[PictureMode]:
        """List of available sound modes."""
        return self._get_list("PV")

    @property
    def ecoMode(self) -> Optional[EcoMode]:
        """Current ECO mode."""
        return self._get_current("ECO")

    @property
    def ecoModeList(self) -> List[EcoMode]:
        """List of available exo modes."""
        return self._get_list("ECO")

    @property
    def channelsBias(self) -> Mapping[ChannelBias, float]:
        return self._get_current("CV")

    @property
    def channelsBiasList(self) -> List[ChannelBias]:
        """List of currently available."""
        return [x for x in self._get_current("CV").keys()]

    @property
    def drcMode(self) -> Optional[DRCMode]:
        """Current ECO mode."""
        return self._get_current("PSDRC")

    @property
    def drcModeList(self) -> List[DRCMode]:
        """List of available sound modes."""
        return self._get_list("PSDRC")

    @property
    def dynamicVolumeMode(self) -> Optional[DynamicMode]:
        """Current ECO mode."""
        return self._get_current("PSDYNVOL")

    @property
    def dynamicVolumeModeList(self) -> List[DynamicMode]:
        """List of available sound modes."""
        return self._get_list("PSDYNVOL")

    @property
    def delay(self) -> Optional[int]:
        """Current delay level."""
        return self._get_current("PSDEL")
        
    @property
    def soundLFE(self) -> Optional[int]:
        """Current Sound LFE level."""
        return self._get_current("PSLFE")

    @property
    def soundBass(self, zone: Zone) -> Optional[int]:
        """Current Sound Bass correction."""
        if zone == zone.MainZone:
          return self._get_current("PSBAS")        
        elif zone == zone.Zone2:
          return self._get_current("Z2PSBAS")
        elif zone == zone.Zone3:
          return self._get_current("Z3PSBAS")
        else: raise AvrError("Unknown Zone")      

    @property
    def soundTreble(self, zone: Zone) -> Optional[int]:
        """Current Sound Treble correction."""
        if zone == zone.MainZone:
          return self._get_current("PSTRE")        
        elif zone == zone.Zone2:
          return self._get_current("Z2PSTRE")
        elif zone == zone.Zone3:
          return self._get_current("Z3PSTRE")
        else: raise AvrError("Unknown Zone")              

    @property
    def soundToneControl(self) -> Optional[bool]:
        """Current Sound Tone Control status."""
        return self._get_current("PSTONE")

    @property
    def tunerStationName(self) -> str:
        """Current tuner station name (RDS or DAB)."""
        if self._get_current("DASTN"):
            return self._get_current("DASTN")
        elif self._get_current("PSTONE"):
            return self._get_current("PSTONE")
        else:
            return None

    @property
    def tunerPreset(self) -> Optional[bool]:
        """Current tuner preset."""
        return self._get_current("TPAN")
        
    def doRefresh(self) -> None:
        """Refresh all properties from the AVR."""

        for cmd_def in self.CMDS_DEFS:
            if cmd_def in NEEDSPACE:
                qs = " ?"
            else:
                qs = "?"
            if not (cmd_def in NOTTOREFRESH):
                logging.debug(f"Refresh for '{self.CMDS_DEFS[cmd_def].label}' ['{cmd_def}']")
                fut = self.write_queue.put_nowait((cmd_def, qs))
        for cmd_def in ADDTOREFRESH:
            if cmd_def in NEEDSPACE:
                qs = " ?"
            else:
                qs = "?"
            logging.debug(f"Refresh for 'N/A' ['{cmd_def}']")
            fut = self.write_queue.put_nowait((cmd_def, qs))                
                
               

    def doTurnAVROn(self) -> None:
        """Turn the AVR on."""
        self.write_queue.put_nowait(("PW", "ON"))

    def doTurnAVROff(self) -> None:
        """Turn the AVR off."""
        self.write_queue.put_nowait(("PW", "STANDBY"))

    def doTurnOn(self, zone: Zone) -> None:
        """Turn the AVR Zone on."""
        if zone == zone.MainZone:
          self.write_queue.put_nowait(("ZM", "ON"))
        elif zone == zone.Zone2:
          self.write_queue.put_nowait(("Z2", "ON"))
        elif zone == zone.Zone3:
          self.write_queue.put_nowait(("Z3", "ON"))
        else: raise AvrError("Unknown Zone")          
        
    def doTurnOff(self, zone: Zone) -> None:
        """Turn the AVR Zone off."""
        if zone == zone.MainZone:
          self.write_queue.put_nowait(("ZM", "OFF"))
        elif zone == zone.Zone2:
          self.write_queue.put_nowait(("Z2", "OFF"))
        elif zone == zone.Zone3:
          self.write_queue.put_nowait(("Z3", "OFF"))
        else: raise AvrError("Unknown Zone")         
        
    def doMuteVolume(self, zone: Zone, value: bool) -> None:
        """Mute or unmute the volume of the zone
        
        Arguments:
        value -- True to mute, False to unmute.
        """
        
        if zone == zone.MainZone:
          self.write_queue.put_nowait(("MU", _on_off_from_bool(value)))
        elif zone == zone.Zone2:
          self.write_queue.put_nowait(("Z2MU", _on_off_from_bool(value)))
        elif zone == zone.Zone3:
          self.write_queue.put_nowait(("Z3MU", _on_off_from_bool(value)))
        else: raise AvrError("Unknown Zone")              
        
    def doSetVolume(self, zone: Zone, value: float) -> None:
        """Set the volume level.
        
        Arguments:
        value -- An integer value between 0 and `max_volume`.
        """
        if value > self.maxvol:
            value = maxvol
        if int(10 * value) % 10:
            # Needs to be a nultiple of 5
            value = int(5 * round(10 * value / 5))
        else:
            value = int(value)
            
        if zone == zone.MainZone:
          self.write_queue.put_nowait(("MV", f"{value:02}"))
        elif zone == zone.Zone2:
          self.write_queue.put_nowait(("Z2", f"{value:02}"))
        elif zone == zone.Zone3:
          self.write_queue.put_nowait(("Z3", f"{value:02}"))
        else: raise AvrError("Unknown Zone")  
        
    def doVolumeUp(self, zone: Zone) -> None:
        """Turn the volume level up one notch."""
        
        if zone == zone.MainZone:
          self.write_queue.put_nowait(("MV", "UP"))
        elif zone == zone.Zone2:
          self.write_queue.put_nowait(("Z2", "UP"))
        elif zone == zone.Zone3:
          self.write_queue.put_nowait(("Z3", "UP"))
        else: raise AvrError("Unknown Zone")          
        
    def doVolumeDown(self, zone: Zone) -> None:
        """Turn the volume level down one notch."""
        
        if zone == zone.MainZone:
          self.write_queue.put_nowait(("MV", "DOWN"))
        elif zone == zone.Zone2:
          self.write_queue.put_nowait(("Z2", "DOWN"))
        elif zone == zone.Zone3:
          self.write_queue.put_nowait(("Z3", "DOWN"))
        else: raise AvrError("Unknown Zone")   
        
    def doSetChannelBias(self, value) -> None:
        """Set the volume level.

        Arguments:
        value  -- chan: channel to set; level:a float value between -12.0 and +12.0
        """
               
        chan = value["chan"]
        if isinstance(chan, str):
            try:           
              chanEnum=ChannelBias(chan)
              logging.debug(f"Converting '{chan}' into enum: {chanEnum.name}:{chanEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown Channel {chan}")
        elif isinstance(chan, ChannelBias):
            chanEnum=chan
        else:
            raise AvrError("Unknown Channel")
            
        level = value["level"]
        if chanEnum not in self.channels_bias:
            logging.warning(f"Channel {chanEnum.name} is not available right now.")
            return

        if self.channels_bias[chanEnum] != level:
            level = level + 50  # 50 is 0dB
            if level < 38:
                level = 38
            elif level > 62:
                level = 62
            if int(10 * level) % 10:
                # Needs to be a nultiple of 5
                level = int(5 * round(10 * level / 5))
            else:
                level = int(level)

            cmd = chanEnum.value
            self.write_queue.put_nowait(("CV", f"{cmd} {level:02}"))
         
    def doChannelBiasUp(self, value: Union[str, ChannelBias]) -> None:
        """Turn the volume level up one notch."""
        
        if isinstance(value, str):
            try:           
              chanEnum=ChannelBias(value)
              logging.debug(f"Converting '{value}' into enum: {chanEnum.name}:{chanEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown Channel {value}")
        elif isinstance(value, ChannelBias):
            chanEnum=value
        else:
            raise AvrError("Unknown Channel")        
            
        if chanEnum not in self.channels_bias:
            logging.warning(f"Channel {chanEnum.name} is not available right now.")
            return
        if self.channels_bias[chanEnum] == 12:
            # We are at the limit. It won't respond
            logging.debug(f"Channel {chanEnum.name} it at the upper limit.")
            return
        cmd = chanEnum.value
        self.write_queue.put_nowait(("CV", f"{cmd} UP"))

    def doChannelBiasDown(self, value: Union[str, ChannelBias]) -> None:
        """Turn the volume level down one notch."""

        if isinstance(value, str):
            try:           
              chanEnum=ChannelBias(value)
              logging.debug(f"Converting '{value}' into enum: {chanEnum.name}:{chanEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown Channel {value}")
        elif isinstance(value, ChannelBias):
            chanEnum=value
        else:
            raise AvrError("Unknown Channel")  
            
        if chanEnum not in self.channels_bias:
            logging.warning(f"Channel {chanEnum.name} is not available right now.")
            return
        if self.channels_bias[chanEnum] == -12:
            # We are at the limit. It won't respond
            logging.debugf(f"Channel {chanEnum.name} it at the lower limit.")
            return

        cmd = chanEnum.value
        self.write_queue.put_nowait(("CV", f"{cmd} DOWN"))

    def doChannelsBiasReset(self) -> None:
        self.write_queue.put_nowait(("CV", "ZRL"))

    def doSelectSource(self, zone: Zone, value: Union[str, InputSource]) -> None:
        """Select the input source."""
        
        if isinstance(value, str):
            try:           
              sourceEnum=InputSource(value)
              logging.debug(f"Converting '{value}' into enum: {sourceEnum.name}:{sourceEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown Source {value}")
        elif isinstance(value, InputSource):
            sourceEnum=value
        else:
            raise AvrError("Unknown Source")
            
        if zone == zone.MainZone:
          self.write_queue.put_nowait(("SI", sourceEnum.value))
        elif zone == zone.Zone2:
          self.write_queue.put_nowait(("Z2", sourceEnum.value))
        elif zone == zone.Zone3:
          self.write_queue.put_nowait(("Z3", sourceEnum.value))
        else: raise AvrError("Unknown Zone")               
        
    def doSelectSoundMode(self, value: Union[str, SurroundMode]) -> None:
        """Select the sound mode."""
        
        if isinstance(value, str):
            try:           
              modeEnum=SurroundMode(value)
              logging.debug(f"Converting '{value}' into enum: {modeEnum.name}:{modeEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown sound mode {value}")
        elif isinstance(value, SurroundMode):
            modeEnum=value
        else:
            raise AvrError("Unknown sound mode")
            
        self.write_queue.put_nowait(("MS", modeEnum.value))

    def doSelectPictureMode(self, value: Union[str, PictureMode]) -> None:
        """Select the picture mode."""
        
        if isinstance(value, str):
            try:           
              modeEnum=PictureMode(value)
              logging.debug(f"Converting '{value}' into enum: {modeEnum.name}:{modeEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown picture mode {value}")
        elif isinstance(value, PictureMode):
            modeEnum=value
        else:
            raise AvrError("Unknown picture mode")
            
        self.write_queue.put_nowait(("PV", modeEnum.value))

    def doSelectEcoMode(self, value: Union[str, EcoMode]) -> None:
        """Select the eco mode."""
        
        if isinstance(value, str):
            try:           
              modeEnum=EcoMode(value)
              logging.debug(f"Converting '{value}' into enum: {modeEnum.name}:{modeEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown eco mode {value}")
        elif isinstance(value, EcoMode):
            modeEnum=value
        else:
            raise AvrError("Unknown eco mode")
            
        self.write_queue.put_nowait(("ECO", modeEnum.value))

    def doSetDelay(self, value: int) -> None:
        """Set the volume delay (in ms)

        Arguments:
        value -- An integer value between 0 and `999`.
        """
        
        if value < 0:
            value = 0
        if value > 999:
            value = 999
        self.write_queue.put_nowait(("PSDEL", f" {value:03}"))

    def doSelectDRCMode(self, value: Union[str, DRCMode]) -> None:
        """Select the drc mode."""
        
        if isinstance(value, str):
            try:           
              modeEnum=DRCMode(value)
              logging.debug(f"Converting '{value}' into enum: {modeEnum.name}:{modeEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown drc mode {value}")
        elif isinstance(value, DRCMode):
            modeEnum=value
        else:
            raise AvrError("Unknown drc mode")
            
        self.write_queue.put_nowait(("PSDRC", " " + modeEnum.value))

    def doSelectDynamicVolumeMode(self, value: Union[str, DynamicMode]) -> None:
        """Select the sound mode."""
        
        if isinstance(value, str):
            try:           
              modeEnum=DynamicMode(value)
              logging.debug(f"Converting '{value}' into enum: {modeEnum.name}:{modeEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown dynamic volume mode {value}")
        elif isinstance(value, DynamicMode):
            modeEnum=value
        else:
            raise AvrError("Unknown dynamic volume mode")
            
        self.write_queue.put_nowait(("PSDYNVOL", " " + modeEnum.value))
        
    def doSoundLFE(self, value: int) -> None:
        """Set level of sound low-frequency effects (LFE)
        
        Arguments:
        value -- level in dB (from -10 to 0)
        """
        value=-value
        if value<-10:
            value=-10 #min
        elif value>0:
            value=0 #max
        self.write_queue.put_nowait(("PSLFE", f" {value:02}"))
                
    def doSoundBass(self, zone:Zone, value: int) -> None:
        """Set level of sound bass for a zone
        
        Arguments:
        value -- level in dB (from -10 to +10)
        """
        value=value+40
        if value<40:
            value=40 #min
        elif value>60:
            value=60 #max
        if zone == zone.MainZone:
          self.write_queue.put_nowait(("PSBAS", f" {value:02}"))
        elif zone == zone.Zone2:
          self.write_queue.put_nowait(("Z2PSBAS", f" {value:02}"))
        elif zone == zone.Zone3:
          self.write_queue.put_nowait(("Z3PSBAS", f" {value:02}"))
        else: raise AvrError("Unknown Zone")             

    def doSoundTreble(self, zone:Zone, value: int) -> None:
        """Set level of sound treble for a zone
        
        Arguments:
        value -- level in dB (from -10 to +10)
        """
        value=value+40
        if value<40:
            value=40 #min
        elif value>60:
            value=60 #max
        if zone == zone.MainZone:
          self.write_queue.put_nowait(("PSTRE", f" {value:02}"))
        elif zone == zone.Zone2:
          self.write_queue.put_nowait(("Z2PSTRE", f" {value:02}"))
        elif zone == zone.Zone3:
          self.write_queue.put_nowait(("Z3PSTRE", f" {value:02}"))
        else: raise AvrError("Unknown Zone")             
        
    def doTunerPreset(self, value: int) -> None:
        """ Set tuner preset
        
        Arguments:
        value -- tuner preset
        """
        if value<1:
            value=1 #min
        elif value>56:
            value=56 #max
        self.write_queue.put_nowait(("TPAN", f"{value:02}"))
    
    def notifyme(self, funcCmd: Callable, funcEvent:Callable) -> None:
        """Register a callback for when a command or an event happens.
        """
        
        if funcCmd:
            self.notifyCmd = funcCmd
        if funcEvent:
            self.notifyEvent = funcEvent        
       
    def close(self):
        self.alive = False
        self._writer.close()
        self.rtask.cancel()
        self.wtask.cancel()
        self.ptask.cancel()
        logging.debug(f"Closed device '{self.name}'")
        if self.notifyEvent:
            self.notifyEvent(self, EventAVR.Close, {})        

    def timeout(self) -> bool:
        logging.debug(f"Timeout #{self._timeoutCnt}...")
        if self.notifyEvent:
            self.notifyEvent(self, EventAVR.TimeOut, {})
        self.close()
        return True

    # API ends here

    async def _send_command(self, cmd: str, val: Any) -> asyncio.Future:
        tosend = f"{cmd}{val}\r"
        logging.debug(f"Sending {tosend}")
        self._writer.write(tosend.encode())
        try:
            await self._writer.drain()
        except asyncio.CancelledError as e:
            return            
        logging.debug("Write drained")

    def _process_response(self, response: str) -> Optional[str]:
        matches = [cmd for cmd in self.CMDS_DEFS.keys() if response.startswith(cmd)] + [
            cmd for cmd in EXTRAS if response.startswith(cmd)
        ]

        if not matches:
            logging.debug(f"!! There is no parser for command {response}")
            return None

        if len(matches) > 1:
            matches.sort(key=len, reverse=True)
        match = matches[0]

        if getattr(self, "_parse_" + match, None):
            #logging.debug(f"Executing _parse_{match}...")
            getattr(self, "_parse_" + match)(response.strip()[len(match) :].strip())
        else:
            # A few special cases ... for now
            if response.startswith("SSINFAISFSV"):
                #logging.debug(f"executing special parsing...")
                try:
                    sr = int(only_int(response.split(" ")[-1]))
                    if sr > 200:
                        sr = round(sr / 10, 1)
                    else:
                        sr = float(sr)
                    self.status["Sampling Rate"] = sr
                except Exception as e:
                    if response.split(" ")[-1] == "NON":
                        self.status["Sampling Rate"] = "-"
                    else:
                        logging.debug(f"Error with sampling rate: {e}")
            else:
                #logging.debug(f"_parse_{match} is not defined; executing _parse_many...")
                self._parse_many(match, response.strip()[len(match) :].strip())

        return match

    def _parse_many(self, cmd: str, resp: str) -> None:
        #logging.debug(f"_parse_many({cmd}, {resp}):")
        if cmd in self.CMDS_DEFS:
            for x in self.CMDS_DEFS[cmd].values:
                if resp == x.value:
                    #logging.debug(f"found a value: {x.name}:{x.value}")
                    code = self.CMDS_DEFS[cmd].code
                    if self.status[code] != x:
                        self.status[code] = x
                    if self.notifyCmd:
                        try:
                            self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])
                        except Exception as e:
                            logging.error('Fatal error when notifyCmd: '+str(e))
                            logging.info(traceback.format_exc())
        else:
            logging.debug(f"There is no parsing for command {cmd}")

    def _parse_control_on_off(self, resp, cmd: str) -> None:
        nval = resp == "ON"
        code = self.CMDS_DEFS[cmd].code
        if self.status[code] != nval:
            self.status[code] = nval
        if self.notifyCmd:
            self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])

    def _parse_speaker_level(self, resp, cmd: str) -> None:
        level = only_int(resp)
        if level:
            level = int(level) - 50
            code = self.CMDS_DEFS[cmd].code
            if self.status[code] != level:
                self.status[code] = level
            if self.notifyCmd:
                self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])

    def _parse_string(self, resp, cmd: str) -> None:
        code = self.CMDS_DEFS[cmd].code
        resp=resp.replace("_", " ")
        resp=resp.strip()
        self.status[code] = resp
        if self.notifyCmd:
            self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])

    def _parse_int(self, resp, cmd: str, minInt:int, maxInt:int ) -> None:
        value = only_int(resp)
        if value:
            value = int(value)
            if value<minInt:
                value=minInt
            if value>maxInt:
                value=maxInt
            code = self.CMDS_DEFS[cmd].code
            if self.status[code] != value:
                self.status[code] = value
            if self.notifyCmd:
                self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])

    def _parse_MV(self, resp: str) -> None:
        level = only_int(resp)
        cmd="MV"
        if level:
            if len(level) > 2:
                level = int(level) / 10
            else:
                level = float(level)

            if resp.startswith("MAX"):
                self.maxvol = level
                logging.debug(f"Set maxvol to {level}")
            else:
                code = self.CMDS_DEFS[cmd].code
                if self.status[code] != level:
                    self.status[code] = level
                if self.notifyCmd:
                    self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])

    def _parse_MU(self, resp: str) -> None:
        self._parse_control_on_off(resp, "MU")

    def _parse_Z2MU(self, resp: str) -> None:
        self._parse_control_on_off(resp, "Z2MU")

    def _parse_Z3MU(self, resp: str) -> None:
        self._parse_control_on_off(resp, "Z3MU")

    def _parse_zone(self, zone: str, resp: str) -> None:
        """ Naturaly, those idiots had tn  overload the zone prefix for
        power, volume and source...
        """
        if resp in ["ON", "OFF"]:
            self._parse_many(zone, resp)
            return

        if resp.startswith("SMART"):
            # not handled
            return

        if resp.startswith("FAVORITE"):
            # not handled, learn to spell!
            return

        if resp.startswith("PSBAS"):
            # Sound bass level
            logging.debug(f"Checking sound bass level for {zone}")
            match="PSBAS"
            resp=resp.strip()[len(match) :].strip()
            self._parse_speaker_level(resp, zone + match)
            return

        if resp.startswith("PSTRE"):
            # Sound treble level
            logging.debug(f"Checking sound treble level for {zone}")
            match="PSTRE"
            resp=resp.strip()[len(match) :].strip()
            self._parse_speaker_level(resp, zone + match)            
            return

        try:            
            level = only_int(resp)
            if len(level) > 2:
                level = int(level) / 10
            else:
                level = float(level)
            logging.debug(f"Checking level for {zone}")
            cmd=zone + "MV"
            code = self.CMDS_DEFS[cmd].code
            if self.status[code] != level:
                self.status[code] = level
            if self.notifyCmd:
                self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])
        except:
            # Probably the source
            try:
                logging.debug(f"Checking source for {zone}")
                self._parse_many(zone + "SI", resp)
            except Exception as e:
                logging.debug(f"Failed when parsing {zone}: {e}")

    def _parse_Z2(self, resp: str) -> None:
        self._parse_zone("Z2", resp)

    def _parse_Z3(self, resp: str) -> None:
        self._parse_zone("Z3", resp)

    def _parse_CV(self, resp: str) -> None:
        """ Different here... Needs to be reset"""
        cmd="CV"
        if resp == "END":
            self.cvend = True
            if self.notifyCmd:
                code = self.CMDS_DEFS[cmd].code
                if self.status[code]:
                    logging.debug(f"My Channel Bias is now {_dict_enum_to_string(self.status[code])}")
                else:
                    logging.debug(f"My Channel Bias is empty")
                self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])
                
        else:
            if self.cvend:
                self.status[self.CMDS_DEFS[cmd].code] = {}
                self.cvend = False
            
            spkr, level = resp.split(" ")
                
            if level:
                if len(level) > 2:
                    level = int(level) / 10
                else:
                    level = float(level)
            level -= 50
            
            spkrEnum=None
            for x in self.CMDS_DEFS[cmd].values:
                if x.value == spkr:
                    spkrEnum = x
                    break
            if spkrEnum:
                self.status[self.CMDS_DEFS[cmd].code][spkrEnum] = level
            else:
                logging.debug(f"Unknown speaker code {spkr}")

    def _parse_SSSOD(self, resp: str) -> None:
        """ Different here..."""
        #logging.debug(f"_parse_SSSOD({resp})")
        #GDE BUG correction
        cmd="SSSOD"
        if resp == "END":
            logging.debug(f"My source list is now {_list_enum_to_string(self.mysources)}")
            if self.notifyCmd:
                self.notifyCmd(self, self.CMDS_DEFS[cmd], self.mysources)            
            logging.debug(f"My source (not used) is now {_list_enum_to_string(self.mysourcesNotUsed)}")
            return
        si, f = resp.split(" ")
        if f == "USE":
            for x in self.CMDS_DEFS[cmd].values:
                if si == x.value:
                    self.mysources.append(x)
                    logging.debug(f"Adding source {x}")
                    break
        if f == "DEL":
            for x in self.CMDS_DEFS[cmd].values:
                if si == x.value:
                    self.mysourcesNotUsed.append(x)
                    logging.debug(f"Adding NOT USED source {x}")
                    break


    def _parse_MS(self, resp: str) -> None:
        """ Different here... What we get is not what we send. So we try to transform
        the result through semi-clever string manipulation
        """
        cmd="MS"
        respTransformed = resp.replace("+", " ")
        respTransformed = " ".join([x.title() for x in respTransformed.split(" ")])
        for old, new in SSTRANSFORM:
            respTransformed = respTransformed.replace(old, new)
        # Clean up spaces
        respTransformed = re.sub(r"[_\W]+", " ", respTransformed)
        respTransformed = respTransformed.strip()
        
        try:           
            if "PURE DIRECT" in resp:
              modeEnum=SurroundMode.PureDirect
            elif "DIRECT" in resp:
              modeEnum=SurroundMode.Direct
            elif "M CH" in resp or "MULTI C" in resp:
              modeEnum=SurroundMode.DolbyDigital
            elif "AAC" in resp:
              modeEnum=SurroundMode.DolbyDigital
            elif "DOLBY" in resp:
              modeEnum=SurroundMode.DolbyDigital
            elif "DTS" in resp or "AL:X" in resp:
              modeEnum=SurroundMode.DtsSurround
            else:
              modeEnum=SurroundMode(resp)
            logging.debug(f"Converting '{resp}' into enum: {modeEnum.name}:{modeEnum.value}")
        except ValueError as e:
            logging.info(f"Unknown sound mode {resp}")
            return            
        
        code = self.CMDS_DEFS[cmd].code
        
        if self.status[code] != modeEnum:
            self.status[code] = modeEnum
        if self.notifyCmd:
            self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])

    def _parse_PSDEL(self, resp: str) -> None:
        self._parse_int(resp, "PSDEL", 0, 300)

    def _parse_PSBAS(self, resp: str) -> None:
        self._parse_speaker_level(resp, "PSBAS")
        
    def _parse_PSTRE(self, resp: str) -> None:
        self._parse_speaker_level(resp, "PSTRE")
        
    def _parse_PSLFE(self, resp: str) -> None:
        """ Parse LFE Level 00 .. 10 => 0db .. - 10 db
        """
        
        cmd="PSLFE"
        level = only_int(resp)
        if level:
            level = - int(level)
            code = self.CMDS_DEFS[cmd].code
            if self.status[code] != level:
                self.status[code] = level
            if self.notifyCmd:
                self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])        

    def _parse_PSTONE(self, resp: str) -> None:
        if resp.startswith("CTRL"):
            code, resp = resp.split(" ")
            self._parse_control_on_off(resp, "PSTONE")

    def _parse_DASTN(self, resp: str) -> None:
        self._parse_string(resp, "DASTN")
        #Clear RDS tuner station name
        self._clear_current("TFANNAME") 
        
    def _parse_TFANNAME(self, resp: str) -> None:
        self._parse_string(resp, "TFANNAME")
        #Clear RDS tuner station name
        self._clear_current("DASTN")        

    def _parse_TPAN(self, resp: str) -> None:
        self._parse_int(resp, "TPAN", 1, 56)

    def _parse_TMAN(self, resp: str) -> None:
        self._parse_string(resp, "TMAN")

        
    async def _do_read(self):
        """ Keep on reading the info coming from the AVR"""

        while self.alive:
            data = b""
            try:
                while not data or data[-1] != ord("\r"):
                    char = await self._reader.read(1)
                    if char == b"":
                        break
                    data += char
            except asyncio.CancelledError as e:
                return            

            if data == b"":
                # Gone
                self.close()
                return

            logging.debug("Received: {}".format(data.decode().strip("\r")))
            self._lastMessageTime=time.time()
            try:
                match = self._process_response(data.decode().strip("\r"))
            except Exception as e:
                logging.debug("Problem processing response: {} - {}".format(e, data.decode().strip("\r")))
                logging.debug(traceback.format_exc())

    async def _do_write(self):
        """ Keep on reading the info coming from the AVR"""

        while self.alive:
            try:
                cmd, param = await self.write_queue.get()
                if cmd:
                    await self._send_command(cmd, param)
                self.write_queue.task_done()
            except asyncio.CancelledError as e:
                return            

    async def _do_ping(self):
        """ Send a ping to the AVR every _pingFreq s"""
        while self.alive:
            try:
                logging.debug("Send ping ...")
                self.write_queue.put_nowait(("PW", "?"))
                if self.notifyEvent:
                    self.notifyEvent(self, EventAVR.Ping, {})                
                await asyncio.sleep(self._timeout)
                #check timeout
                delayLastMessage = time.time() - self._lastMessageTime
                logging.debug(f"Last message received {delayLastMessage:.2f}s ago")
                if delayLastMessage>self._timeout:
                    self._timeoutCnt=self._timeoutCnt+1
                    if self.timeout():
                        return
                else:
                    self._timeoutCnt=0 
                await asyncio.sleep(self._pingFreq - self._timeout)                    
            except asyncio.CancelledError as e:
                return
            except Exception as e:
                logging.debug("Problem processing ping: {} - {}".format(e, e.__class__.__name__))  
                logging.debug(traceback.format_exc())                
                await asyncio.sleep(self._pingFreq)
  