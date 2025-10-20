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


async def avr_factory(serial: str, host: str, port: int = 23, timeout: float = 3.0) -> "MDAVR":
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
        return MDAVR(serial, reader, writer, timeout)
    except asyncio.TimeoutError as e:
        #logging.debug("error when connecting to '{}': timeout".format(host))
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

def _dict_enum_to_string(myDict: Mapping[Enum, Any]) -> str:
    return "["+",".join([""+x.name+":"+x.value+" => "+str(myDict[x]) for x in myDict])+"]"


class _CommandDef:
    code: str
    codeRequest: str
    label: str
    zone: Zone
    values: Optional[Enum]

    def __init__(self, code: str, codeRequest: str, label: str, zone, vals: Any):
        self.code = code
        self.codeRequest = codeRequest
        self.label = label
        self.values = vals
        self.zone = zone

class MDAVR:
    """Connection to a Denon AVR over Telnet.

    Uses `connect` to create a connection to the AVR.
    """

    CMDS_DEFS: Mapping[str, _CommandDef] = {
        "PW": _CommandDef("PW", "PW?", "Main Power", Zone.UndefinedZone, Power),
        "ZM": _CommandDef("ZM", "ZM?", "Power", Zone.MainZone, Power),
        "Z2": _CommandDef("Z2", "Z2?", "Power", Zone.Zone2, Power),
        "Z3": _CommandDef("Z3", "Z3?", "Power", Zone.Zone3, Power),
        "MU": _CommandDef("MU", "MU?", "Muted", Zone.MainZone, None),
        "Z2MU": _CommandDef("Z2MU", "Z2MU?", "Muted", Zone.Zone2, None),
        "Z3MU": _CommandDef("Z3MU", "Z3MU?", "Muted", Zone.Zone3, None),
        "MV": _CommandDef("MV", "MV?", "Volume", Zone.MainZone, None),
        "Z2MV": _CommandDef("Z2MV", "Z2?", "Volume", Zone.Zone2, None),
        "Z3MV": _CommandDef("Z3MV", "Z3?", "Volume", Zone.Zone3, None),
        "SI": _CommandDef("SI", "SI?", "Source", Zone.MainZone, InputSource),
        "Z2SI": _CommandDef("Z2SI", "Z2?", "Source", Zone.Zone2, InputSource),
        "Z3SI": _CommandDef("Z3SI", "Z3?", "Source", Zone.Zone3, InputSource),
        "SV": _CommandDef("SV", "SV?", "Video Mode", Zone.UndefinedZone, InputSource),
        "MS": _CommandDef("MS", "MS?", "Surround Mode", Zone.UndefinedZone, SurroundMode),
        "CV": _CommandDef("CV", "CV?", "Channel Bias", Zone.UndefinedZone, Channel),
        "PV": _CommandDef("PV", "PV?", "Picture Mode", Zone.UndefinedZone, PictureMode),
        "ECO": _CommandDef("ECO", "ECO?", "Eco Mode", Zone.UndefinedZone, EcoMode),

        "SSSOD": _CommandDef("SSSOD", "SSOD ?", "Available Source", Zone.UndefinedZone, InputSource),
        "SSFUN": _CommandDef("SSFUN", "SSFUN ?", "Source Name", Zone.UndefinedZone, InputSource),
        "SSLAN": _CommandDef("SSLAN", "SSLAN ?", "Language", Zone.UndefinedZone, None),
        "SSSMG": _CommandDef("SSSMG", "SSSMG ?", "Sound Mode", Zone.UndefinedZone, SoundMode),
        "SSLEV": _CommandDef("SSLEV", "SSLEV ?", "Channel Level", Zone.UndefinedZone, Channel),
        "SSINFFRM": _CommandDef("SSINFFRM", "SSINFFRM ?", "Microcode Version", Zone.UndefinedZone, None),
        "SSLOC": _CommandDef("SSLOC", "SSLOC ?", "Lock", Zone.UndefinedZone, None),

        "PSDEL": _CommandDef("PSDEL", "PSDEL ?", "Sound Delay", Zone.UndefinedZone, None),
        "PSDRC": _CommandDef("PSDRC", "PSDRC ?", "Dynamic Range Compression", Zone.UndefinedZone, DRCMode),
        "PSDYNVOL": _CommandDef("PSDYNVOL", "PSDYNVOL ?", "Dynamic Volume", Zone.UndefinedZone, DynamicVolume),
        "PSLFE": _CommandDef("PSLFE", "PSLFE ?", "Sound LFE", Zone.UndefinedZone, None),
        "PSBAS": _CommandDef("PSBAS", "PSBAS ?", "Sound Bass", Zone.MainZone, None),
        "Z2PSBAS": _CommandDef("Z2PSBAS", "Z2PSBAS ?", "Sound Bass", Zone.Zone2, None),
        "Z3PSBAS": _CommandDef("Z3PSBAS", "Z3PSBAS ?", "Sound Bass", Zone.Zone3, None),
        "PSTRE": _CommandDef("PSTRE", "PSTRE ?", "Sound Treble", Zone.MainZone, None),
        "Z2PSTRE": _CommandDef("Z2PSTRE", "Z2PSTRE ?", "Sound Treble", Zone.Zone2, None),
        "Z3PSTRE": _CommandDef("Z3PSTRE", "Z3PSTRE ?", "Sound Treble", Zone.Zone3, None),
        "PSTONE": _CommandDef("PSTONE", "PSTONE CTRL ?", "Sound Tone Control", Zone.UndefinedZone, None),
        "PSCLV": _CommandDef("PSCLV", "PSCLV ?", "Center Level", Zone.UndefinedZone, None),
        "PSSWL": _CommandDef("PSSWL", "PSSWL ?", "Subwoofer Level", Zone.UndefinedZone, None),
        "PSHEQ": _CommandDef("PSHEQ", "PSHEQ ?", "Headphone EQ", Zone.UndefinedZone, None),
        "PSDYNEQ": _CommandDef("PSDYNEQ", "PSDYNEQ ?", "Dynamic EQ", Zone.UndefinedZone, None),
        "PSREFLEV": _CommandDef("PSREFLEV", "PSREFLEV ?", "Dynamic EQ Reference Level", Zone.UndefinedZone, None),
        "PSRSTR": _CommandDef("PSRSTR", "PSRSTR ?", "Audio Restorer", Zone.UndefinedZone, AudioRestorer),
        
        "DASTN": _CommandDef("DASTN", "DA ?", "Tuner Station Name", Zone.UndefinedZone, None),
        "DAPTY": _CommandDef("DAPTY", "DA ?", "Tuner Program Type", Zone.UndefinedZone, None),       
        "DAENL": _CommandDef("DAENL", "DA ?", "Tuner Ensemble Label", Zone.UndefinedZone, None),
        "DAFRQ": _CommandDef("DAFRQ", "DA ?", "Tuner Frequency", Zone.UndefinedZone, None),   
        "DAQUA": _CommandDef("DAQUA", "DA ?", "Tuner Quality", Zone.UndefinedZone, None),   
        "DAINF": _CommandDef("DAINF", "DA ?", "Tuner Audio Information", Zone.UndefinedZone, None),           
        "TFANNAME": _CommandDef("TFANNAME", "TFANNAME?", "Tuner Station Name", Zone.UndefinedZone, None),
        "TPAN": _CommandDef("TPAN", "TPAN?", "Tuner Preset", Zone.UndefinedZone, None),
        "TMAN": _CommandDef("TMAN", "TMAN?", "Tuner Mode", Zone.UndefinedZone, None),
        "OPTPN": _CommandDef("OPTPN", "OPTPN ?", "Tuner Station List", Zone.UndefinedZone, None),
        
        "R1": _CommandDef("R1", "RR?", "Zone Name", Zone.MainZone, None),
        "R2": _CommandDef("R2", "RR?", "Zone Name", Zone.Zone2, None),
        "R3": _CommandDef("R3", "RR?", "Zone Name", Zone.Zone3, None),
        "SPPR": _CommandDef("SPPR", "SPPR ?", "Speaker Preset", Zone.UndefinedZone, None),
        "BTTX": _CommandDef("BTTX", "BTTX ?", "Bluetooth", Zone.UndefinedZone, None),
        "NSFRN": _CommandDef("NSFRN", "NSFRN ?", "Name", Zone.UndefinedZone, None),
        "STBY": _CommandDef("STBY", "STBY?", "Standby", Zone.UndefinedZone, Standby),

        # Notes:
        # ------
        # RR?   Get the list of zones with associated Name => Reply 
        #       R1xxx
        #       R2xxxx ...
        # DA ?  Get the status of tuner => Reply
        #       DASTN Long Station Name
        #       DAPTY Program Type
        #       DAENL Ensemble Label
        #       DAFRQ Frequency
        #       DAQUA Quality
        #       DAINF Audio Information
        #
        # To be added
        # SSANA ? analog inputs
        # SSHDM ? Mapping between source and HDMI connection
        # SSIPM ?
        # SSDIN ? digital inputs,  COax OPtical
        # SSSPC ? Speakers' detailed configuration
        # SSPAA ? Speakers' configuration
		#		'FRB' => '5.1-Channel+FrontB',			
		#		'BIA' => '5.1-Channel (Bi-Amp)',	
		#		'ZO2' => '5.1-Channel+Zone2',
		#		'ZO3' => '5.1-Channel+Zone3',
		#		'ZOM' => '5.1-Channel+Zone2/3-Mono',
		#		'NOR' => '7.1-Kanal',
		#		'2CH' => '7.1/2-Channel-Front',
		#		'91C' => '9.1-Channel',
		#		'DAT' => 'Dolby Atmos',
        # SSHOS ?
        #
        # SSQSNZMA ?  List of Quick select name        
        # SSINFMO1INT ? HDMI # for Monitor 1
        # SSINFMO1HDR ? HDR Support for Monitor 1
        # SSINFMO1RES ? List of supported resolution for Monitor 1
        # SSINFMO1FEA ? Advanced function of Monitor 1
        # SSINFMO2INT ? HDMI # for Monitor 2
        # SSINFMO2HDR ? HDR Support for Monitor 2
        # SSINFMO2RES ? List of supported resolution for Monitor 2
        # SSINFMO2FEA ? Advanced function of Monitor 2
        # SSINFAISFSV ? Sampling Rate
        # SSINFAISSIG ? Signal Format
        #   '01' => 'Analog',
	    #   '02' => 'PCM',
		#   '03' => 'Dolby Audio DD',
		#   '04' => 'Dolby TrueHD',
		#   '05' => 'Dolby Atmos',
		#   '06' => 'DTS',
        #   '08' => 'DTS-HD Hi Res',
		#   '09' => 'DTS-HD Mstr',
        #   '12' => 'Dolby Digital',
		#   '13' => 'PCM Zero',   
        # SD? Sound input mode
        #	'AUTO'		=> 'auto',
		#   'HDMI'		=> 'hdmi',
		#   'DIGITAL'	=> 'digital',
		#   'ANALOG'	=> 'analog',
		#   'EXT.IN'	=> 'externalInput',
		#   '7.1IN'		=> '7.1input',
		#   'ARC'		=> 'ARCplaying',
        #   'EARC'      => 'Enhanced ARC'
		#   'NO'		=> 'noInput',
        # OPTPSTUNER ?
        # OPSTS ?
        # SYMODTUN ?    Type of Tuner (EUR, ...)
        # SYMDNOR ?
        # SYSDV ?
        # SYHDMIDIAG ? Diagnostic HMDI
        # VIALL?    
    }

    _reader: asyncio.StreamReader
    _writer: asyncio.StreamWriter
    _timeout: float
    _lastMessageTime: float
    _pingFreq: float
    _timeoutCnt: float

    def __init__(
        self,
        serial: str,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        timeout: float = 3,
        pingFreq: float = 30
    ):
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
        self.sslevend = True
        self.notifyCmd = None
        self.notifyEvent = None
        self.mysources = []
        self.mysourcesNotUsed = []
        self.sourcesName: Mapping[InputSource, str] = {}
        self._lastMessageTime = 0
        self._timeoutCnt = 0
        # Start reading
        self.wtask = asyncio.get_event_loop().create_task(self._do_write())
        self.rtask = asyncio.get_event_loop().create_task(self._do_read())
        self.ptask = asyncio.get_event_loop().create_task(self._do_ping())
        self.doRefresh() 
        if self.notifyEvent:
          self.notifyEvent(self, EventAVR.Init, {})


    def _get_current(self, cmd) -> Any:
        code = self.CMDS_DEFS[cmd].code
        return self.status[code]
        
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
    def surroundMode(self) -> Optional[SurroundMode]:
        """Name of the current surround mode."""
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
    def channelsBias(self) -> Mapping[Channel, float]:
        return self._get_current("CV")

    @property
    def channelsBiasList(self) -> List[Channel]:
        """List of currently available."""
        return [x for x in self._get_current("CV").keys()]

    @property
    def sourceName(self) -> Mapping[InputSource, str]:
        """Name of input sources."""
        return self.sourcesName

    @property
    def soundMode(self) -> Optional[SoundMode]:
        """Name of the current sound mode."""
        return self._get_current("SSSMG")

    @property
    def language (self) -> Optional[str]:
        """ language. """
        return self._get_current("SSLAN")
        
    @property
    def centerLevel (self) -> Optional[float]:
        """ level of center spreaker # """
        channelLevel= self._get_current("SSLEV")
        return channelLevel[Channel.Centre] 

    @property
    def subwooferLevel (self) -> List[float]:
        """ level of subwoofer spreaker # """
        channelLevel= self._get_current("SSLEV")
        if channelLevel[Channel.Subwoofer2]:
            return (channelLevel[Channel.Subwoofer], channelLevel[Channel.Subwoofer2])
        elif channelLevel[Channel.Subwoofer]:
            return (channelLevel[Channel.Subwoofer], 0)
        else:
            return (0, 0)

    @property
    def channelLevel (self) -> Mapping[Channel, float]:
        """ level of channels # """
        return self._get_current("SSLEV")  

    @property
    def microcodeVersion(self) -> Mapping[MicroCodeType, str]:
        """ microcode version # """
        return self._get_current("SSINFFRM")    

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
    def headphoneEQ (self) -> Optional[bool]:
        """ headphone EQ # """
        return self._get_current("PSHEQ") 

    @property
    def dynamicEQ (self) -> Optional[bool]:
        """ dynamic EQ # """
        return self._get_current("PSDYNEQ") 

    @property
    def dynamicEQReferenceLevel (self) -> Optional[int]:
        """ dynamic EQ reference level # """
        return self._get_current("PSREFLEV") 

    @property
    def audioRestorer (self) -> Optional[AudioRestorer]:
        """ Audio restorer # """
        return self._get_current("PSRSTR")        

    @property
    def tunerStationName(self) -> Optional[str]:
        """Current tuner station name (RDS or DAB)."""
        if self._get_current("DASTN"):
            return self._get_current("DASTN")
        elif self._get_current("TFANNAME"):
            return self._get_current("TFANNAME")
        else:
            return None

    @property
    def tunerProgramType(self) -> Optional[str]:
        """Current tuner program type."""
        return self._get_current("DAPTY")

    @property
    def tunerEnsembleLabel(self) -> Optional[str]:
        """Current tuner ensemble label."""
        return self._get_current("DAENL")
        
    @property
    def tunerFrequency(self) -> Optional[str]:
        """Current tuner frequency."""
        return self._get_current("DAFRQ")

    @property
    def tunerQuality(self) -> Optional[int]:
        """Current tuner quality."""
        return self._get_current("DAQUA")

    @property
    def tunerAudioInformation(self) -> Optional[str]:
        """Current tuner audio information."""
        return self._get_current("DAINF")

    @property
    def tunerPreset(self) -> Optional[int]:
        """Current tuner preset."""
        return self._get_current("TPAN")
        
    @property
    def tunerStationList(self) -> Mapping[int, str]:
        """Current tuner preset."""
        return self._get_current("OPTN")
    
    @property
    def zoneName (zone: Zone) -> Optional[str]:
        """Zone name."""
        if zone == zone.MainZone:
          return self._get_current("R1")        
        elif zone == zone.Zone2:
          return self._get_current("R2")
        elif zone == zone.Zone3:
          return self._get_current("R3")
        else: raise AvrError("Unknown Zone")           
        
    @property
    def speakerPreset (self) -> Optional[int]:
        """ spreaker Preset # """
        return self._get_current("SPPR")
    
    @property
    def bluetooth (self) -> Mapping[Bluetooth, Any]:
        """ bluetooth # """
        return self._get_current("BTTX")

    @property
    def deviceName (self) -> Optional[str]:
        """ name of the device # """
        if self._get_current("NSFRN"):
            return self._get_current("NSFRN")
        return f"AVR #{self.serial}"
        
    @property
    def lock(self) -> Optional[bool]:
        """Current Lock status."""
        return self._get_current("SSLOC")      

    @property
    def standby(self) -> Optional[Standby]:
        """Current Standby value."""
        return self._get_current("STBY")      

    #xxxxx#        

    def doRefresh(self) -> None:
        """Refresh all properties from the AVR."""
        
        alreadySent = []
        for cmd_def in self.CMDS_DEFS:
            if not (self.CMDS_DEFS[cmd_def].codeRequest in alreadySent):
                logging.debug(f"Refresh for '{self.CMDS_DEFS[cmd_def].label}' ['{cmd_def}']: '{self.CMDS_DEFS[cmd_def].codeRequest}'")
                self.write_queue.put_nowait((self.CMDS_DEFS[cmd_def].codeRequest, ""))
                alreadySent.append(self.CMDS_DEFS[cmd_def].codeRequest)                     

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
        """Set the bias of the channel.

        Arguments:
        value  -- chan: channel to set; level:a float value between -12.0 and +12.0
        """
               
        chan = value["chan"]
        if isinstance(chan, str):
            try:           
              chanEnum=Channel(chan)
              # logging.debug(f"Converting '{chan}' into enum: {chanEnum.name}:{chanEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown Channel {chan}")
        elif isinstance(chan, Channel):
            chanEnum=chan
        else:
            raise AvrError("Unknown Channel")
            
        level = value["level"]
        channelBias = self._get_current("CV")
        if chanEnum not in channelBias:
            logging.warning(f"Channel {chanEnum.name} is not available right now.")
            return

        if channelBias[chanEnum] != level:
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
         
    def doChannelBiasUp(self, value: Union[str, Channel]) -> None:
        """Turn the bias level up one notch."""
        
        if isinstance(value, str):
            try:           
              chanEnum=Channel(value)
              # logging.debug(f"Converting '{value}' into enum: {chanEnum.name}:{chanEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown Channel {value}")
        elif isinstance(value, Channel):
            chanEnum=value
        else:
            raise AvrError("Unknown Channel")        
            
        channelBias = self._get_current("CV")    
        if chanEnum not in channelBias:
            logging.warning(f"Channel {chanEnum.name} is not available right now.")
            return
        if self.channels_bias[chanEnum] == 12:
            # We are at the limit. It won't respond
            logging.debug(f"Channel {chanEnum.name} it at the upper limit.")
            return
        cmd = chanEnum.value
        self.write_queue.put_nowait(("CV", f"{cmd} UP"))

    def doChannelBiasDown(self, value: Union[str, Channel]) -> None:
        """Turn the bias level down one notch."""

        if isinstance(value, str):
            try:           
              chanEnum=Channel(value)
              # logging.debug(f"Converting '{value}' into enum: {chanEnum.name}:{chanEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown Channel {value}")
        elif isinstance(value, Channel):
            chanEnum=value
        else:
            raise AvrError("Unknown Channel")
            
        channelBias = self._get_current("CV")    
        if chanEnum not in channelBias:
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
              # logging.debug(f"Converting '{value}' into enum: {sourceEnum.name}:{sourceEnum.value}")
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
              # logging.debug(f"Converting '{value}' into enum: {modeEnum.name}:{modeEnum.value}")
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
              # logging.debug(f"Converting '{value}' into enum: {modeEnum.name}:{modeEnum.value}")
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
              # logging.debug(f"Converting '{value}' into enum: {modeEnum.name}:{modeEnum.value}")
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
              # logging.debug(f"Converting '{value}' into enum: {modeEnum.name}:{modeEnum.value}")
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
              # logging.debug(f"Converting '{value}' into enum: {modeEnum.name}:{modeEnum.value}")
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
  
  
    def doLanguage (self, value: str) -> None:
        logging.error("this function 'doLanguage' is not implemented")
        
    def doSpeakerPreset (self, value: int) -> None:
        if value >= 1 and value <=2:
            self.write_queue.put_nowait(("SPPR", f" {value}"))
    
    def doBluetoothTransmitterOn (self) -> None:
        self.write_queue.put_nowait(("BTTX", " ON"))

    def doBluetoothTransmitterOff (self) -> None:
        self.write_queue.put_nowait(("BTTX", " OFF"))

    def doBluetoothOutputMode (self, value: Union[str, BluetoothOutputMode]) -> None:
        """Select the bluetooth output mode."""
        
        if isinstance(value, str):
            try:           
              modeEnum=BluetoothOutputMode(value)
              # logging.debug(f"Converting '{value}' into enum: {modeEnum.name}:{modeEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown bluetooth output mode {value}")
        elif isinstance(value, BluetoothOutputMode):
            modeEnum=value
        else:
            raise AvrError("Unknown bluetooth output mode")
            
        self.write_queue.put_nowait(("BTTX", " " + modeEnum.value))    
        
    def doHeadphoneEQOn (self) -> None:
        self.write_queue.put_nowait(("PSHEQ", " ON"))
        
    def doHeadphoneEQOff (self) -> None:
        self.write_queue.put_nowait(("PSHEQ", " OFF"))        

    def doDynamicEQOn (self) -> None:
        self.write_queue.put_nowait(("PSDYNEQ", " ON"))

    def doDynamicEQOff (self) -> None: 
        self.write_queue.put_nowait(("PSDYNEQ", " OFF"))

    def doDynamicEQReferenceLevel (self, value: int) -> None:
        value = round(value / 5, 0) * 5
        if value<0:
            value=0
        if value>15:
            value=15
        self.write_queue.put_nowait(("PSREFLEV", f" {value}"))
        return self._get_current("PSREFLEV") 

    def doAudioRestorer (self, value: Union[str, AudioRestorer]) -> None:
        """Select the audio restorer mode."""
        
        if isinstance(value, str):
            try:           
              modeEnum=AudioRestorer(value)
              # logging.debug(f"Converting '{value}' into enum: {modeEnum.name}:{modeEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown audio restorer mode {value}")
        elif isinstance(value, AudioRestorer):
            modeEnum=value
        else:
            raise AvrError("Unknown audio restorer mode")
  
        self.write_queue.put_nowait(("PSRSTR", " " + modeEnum.value))    
        
    def doSetLevelChannel(self, value) -> None:
        """Set the level of the channel.

        Arguments:
        value  -- chan: channel to set; level:a float value between -12.0 and +12.0
        """
               
        chan = value["chan"]
        if isinstance(chan, str):
            try:           
              chanEnum=Channel(chan)
              # logging.debug(f"Converting '{chan}' into enum: {chanEnum.name}:{chanEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown Channel {chan}")
        elif isinstance(chan, Channel):
            chanEnum=chan
        else:
            raise AvrError("Unknown Channel")
            
        level = value["level"]
        channelLevel = self._get_current("SSLEV")
        if chanEnum not in channelLevel:
            logging.warning(f"Channel {chanEnum.name} is not available right now.")
            return

        if channelLevel[chanEnum] != level:
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
            self.write_queue.put_nowait(("SSLEV", f"{cmd} {level:02}"))    

    def doLock(self,  value: bool) -> None:
        """Lock or unlock
        
        Arguments:
        value -- True to lock, False to unlock.
        """
        
        self.write_queue.put_nowait(("SSLOC ", _on_off_from_bool(value)))
        
    def doStandby (self, value: Union[str, Standby]) -> None:
        """Select the standby mode."""
        
        if isinstance(value, str):
            try:           
              modeEnum=Standby(value)
              # logging.debug(f"Converting '{value}' into enum: {modeEnum.name}:{modeEnum.value}")
            except ValueError as e:
              raise AvrError(f"Unknown standby mode {value}")
        elif isinstance(value, Standby):
            modeEnum=value
        else:
            raise AvrError("Unknown standby mode")
            
        self.write_queue.put_nowait(("STBY", modeEnum.value))    

    #xxxxx#            
    
    def notifyme(self, funcCmd: Callable, funcEvent:Callable) -> None:
        """Register a callback for when a command or an event happens.
        """
        
        if funcCmd:
            self.notifyCmd = funcCmd
        if funcEvent:
            self.notifyEvent = funcEvent        
       
    def close(self):
        self.alive = False
        logging.info(f"Closing device '{self.deviceName}'")
        self._writer.close()
        self.rtask.cancel()
        self.wtask.cancel()
        self.ptask.cancel()
        logging.info(f"|-> Closed device '{self.deviceName}'")
        if self.notifyEvent:
            self.notifyEvent(self, EventAVR.Close, {})        

    def timeout(self) -> bool:
        self._timeoutCnt=self._timeoutCnt+1
        logging.info(f"Timeout #{self._timeoutCnt} for device '{self.deviceName}'")
        if self._timeoutCnt>=1:
            if self.notifyEvent:
                self.notifyEvent(self, EventAVR.TimeOut, {})
            self.close()
            return True
        return False

    # API ends here

    async def _send_command(self, cmd: str, val: Any) -> asyncio.Future:
        tosend = f"{cmd}{val}\r"
        logging.debug(f"Sending {tosend}")
        self._writer.write(tosend.encode())
        await self._writer.drain()
        logging.debug("|-> Write drained")

    def _process_response(self, response: str) -> Optional[str]:
        matches = [cmd for cmd in self.CMDS_DEFS.keys() if response.startswith(cmd)] 

        if not matches:
            logging.debug(f"!! There is no parser for command {response}")
            return None

        if len(matches) > 1:
            matches.sort(key=len, reverse=True)
        match = matches[0]

        if getattr(self, "_parse_" + match, None):
            # logging.debug(f"Executing _parse_{match}...")
            getattr(self, "_parse_" + match)(response.strip()[len(match) :].strip())
        else:
            # logging.debug(f"_parse_{match} is not defined; executing _parse_many...")
            self._parse_many(match, response.strip()[len(match) :].strip())

        return match

    def _parse_many(self, cmd: str, resp: str) -> None:
        # logging.debug(f"_parse_many({cmd}, {resp}):")
        if cmd in self.CMDS_DEFS:
            if self.CMDS_DEFS[cmd].values is None:
                logging.debug(f"No automatic parser found for command {cmd} {resp}")
            else:  
                for x in self.CMDS_DEFS[cmd].values:
                    if resp == x.value:
                        # logging.debug(f"found a value: {x.name}:{x.value}")
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
        level=only_int(resp)
        if level:
            if len(level) > 3:
                logging.error(f"error when parsing speaker level: level {level} is too big")
            elif len(level) > 2:
                level = int(resp) / 10
            else:
                level = float(resp)        
            level -= 50
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
            if len(level) > 3:
                logging.error(f"error when parsing volume: volume {level} is too big")
            elif len(level) > 2:
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
            if len(level) > 3:
                logging.error(f"error when parsing speaker level: level {level} is too big")    
            elif len(level) > 2:
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
        
    def _parse_SSLEV(self, resp: str) -> None:
        #Special as resp is 'spkr code' + space + 'spkr level'
        cmd="SSLEV"
        code = self.CMDS_DEFS[cmd].code
        if resp == "END":
            self.sslevend = True
            if self.notifyCmd:
                if self.status[code]:
                    logging.debug(f"My Channel level is now {_dict_enum_to_string(self.status[code])}")
                else:
                    logging.debug(f"My Channel level is empty")
                self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])                                        
        else:        
            if self.sslevend:
                self.status[code] = {}
                self.sslevend = False            
            spkr, level = resp.split(" ") 
            if level:
                if len(level) > 3:
                    logging.error(f"error when parsing speaker level: level {level} is too big")        
                elif len(level) > 2:
                    level = int(level) / 10
                else:
                    level = float(level)
            level -= 50
            # logging.debug(f"Speaker code {spkr}")
            try:    
                spkrEnum=Channel(spkr)
                # logging.debug(f"Converting '{spkr}' into enum: {spkrEnum.name}:{spkrEnum.value}")
                self.status[code][spkrEnum] = level
            except ValueError as e:
                logging.debug(f"Unknown Channel {spkr}")

    def _parse_CV(self, resp: str) -> None:
        """ Different here... Needs to be reset"""
        cmd="CV"
        code = self.CMDS_DEFS[cmd].code
        if resp == "END":
            self.cvend = True
            if self.notifyCmd:
                if self.status[code]:
                    logging.debug(f"My Channel Bias is now {_dict_enum_to_string(self.status[code])}")
                else:
                    logging.debug(f"My Channel Bias is empty")
                self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])
                
        else:
            if self.cvend:
                self.status[code] = {}
                self.cvend = False
            
            spkr, level = resp.split(" ")
                
            if level:
                if len(level) > 3:
                    logging.error(f"error when parsing biais: level {level} is too big")    
                if len(level) > 2:
                    level = int(level) / 10
                else:
                    level = float(level)
            level -= 50
            try:
                spkrEnum=Channel(spkr)
                # logging.debug(f"Converting '{spkr}' into enum: {spkrEnum.name}:{spkrEnum.value}")
                self.status[code][spkrEnum] = level
            except ValueError as e:
                logging.debug(f"Unknown Channel {spkr}")

    def _parse_SSSOD(self, resp: str) -> None:
        """ Different here..."""
        # logging.debug(f"_parse_SSSOD({resp})")
        #GDE BUG correction
        cmd="SSSOD"
        if resp == "END":
            logging.debug(f"My source list is now {_list_enum_to_string(self.mysources)}")
            if self.notifyCmd:
                self.notifyCmd(self, self.CMDS_DEFS[cmd], self.mysources)            
            logging.debug(f"My source (not used) is now {_list_enum_to_string(self.mysourcesNotUsed)}")
            return
        si, f = resp.split(" ")
        try:
            x = InputSource(si)
            # logging.debug(f"Converting '{si}' into enum: {x.name}:{x.value}")
            if f == "USE":
                self.mysources.append(x)
                # logging.debug(f"Adding source {x}")
            elif f == "DEL":
                self.mysourcesNotUsed.append(x)
                # logging.debug(f"Adding NOT USED source {x}")
        except ValueError as e:
            logging.debug(f"Unknown source {si}")

    def _parse_SSFUN(self, resp: str) -> None:
        """ Name of the sources... """
        cmd="SSFUN" 
        if resp == "END": 
            logging.debug(f"The names of each source are {self.sourcesName}")
            if self.notifyCmd:
                self.notifyCmd(self, self.CMDS_DEFS[cmd], self.sourcesName)            
            return
        si, sourceName = resp.split(" ", 1)
        try:
            x = InputSource(si)
            #logging.debug(f"Converting '{si}' into enum: {x.name}:{x.value}")
            self.sourcesName[x]=sourceName
            logging.debug(f"Name of source {x}: '{sourceName}'")
        except ValueError as e:
            logging.debug(f"Unknown source {si}")        

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
            #logging.debug(f"Converting '{resp}' into enum: {modeEnum.name}:{modeEnum.value}")
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
        
    def _parse_DAPTY(self, resp: str) -> None:
        self._parse_string(resp, "DAPTY")        
        
    def _parse_DAENL(self, resp: str) -> None:
        self._parse_string(resp, "DAENL")        
        
    def _parse_DAFRQ(self, resp: str) -> None:
        self._parse_string(resp, "DAFRQ")        

    def _parse_DAQUA(self, resp: str) -> None:
        self._parse_int(resp, "DAQUA",0, 100)        

    def _parse_DAINF(self, resp: str) -> None:
        self._parse_string(resp, "DAINF")        

    def _parse_TFANNAME(self, resp: str) -> None:
        self._parse_string(resp, "TFANNAME")
        #Clear RDS tuner station name
        self._clear_current("DASTN")        

    def _parse_TPAN(self, resp: str) -> None:
        self._parse_int(resp, "TPAN", 1, 56)

    def _parse_TMAN(self, resp: str) -> None:
        self._parse_string(resp, "TMAN")

    def _parse_OPTPN(self, resp:str) -> None:
        cmd="OPTPN"
        code = self.CMDS_DEFS[cmd].code
        
        stationId, stationName = resp.split(" ",1)
        stationId=int(only_int(stationId))
        stationName = stationName .strip()
        
        #Check weird format when multiple OPTPN message are concat
        try:
            nextOPTPN = stationName.index(f"OPTPN{(stationId+1):02}")
            resp = stationName[nextOPTPN+5:]
            stationName = stationName[:nextOPTPN]
            self._parse_OPTPN(resp)
        except ValueError as e:
            pass
        
        logging.debug(f"Station '{stationId}': '{stationName}'")  
        if self.status[code] is None:
            self.status[code] = {}
        self.status[code][stationId]=stationName
        
        if stationId>=56 and self.notifyCmd:
            self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])
            #pass
        

    def _parse_R1(self, resp: str) -> None:
        self._parse_string(resp, "R1")

    def _parse_R2(self, resp: str) -> None:
        self._parse_string(resp, "R2")

    def _parse_R3(self, resp: str) -> None:
        self._parse_string(resp, "R3")

    def _parse_SSLAN(self, resp: str) -> None:
        self._parse_string(resp, "SSLAN")

    def _parse_SPPR(self, resp: str) -> None:
        self._parse_int(resp, "SPPR", 1, 2)

    def _parse_BTTX(self, resp: str) -> None:
        cmd="BTTX"
        code = self.CMDS_DEFS[cmd].code
        if (self.status[code] is None):
            self.status[code]={}
        try:
            x = BluetoothTransmitter(resp)
            self.status[code][Bluetooth.Transmitter] = x
            logging.debug(f"BT Transmitter: {x}")
        except Exception as e:
            pass
        try:
            x = BluetoothOutputMode(resp)
            self.status[code][Bluetooth.OutputMode] = x
            logging.debug(f"BT OutputMode: {x}")
        except Exception as e:
            pass       
        if self.notifyCmd:
            self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])

    def _parse_PSCLV(self, resp: str) -> None:
        cmd="SSLEV"
        code = self.CMDS_DEFS[cmd].code
        level=only_int(resp)
        if level:
            if len(level) > 3:
                logging.error(f"error when parsing speaker level: level {level} is too big")        
            elif len(level) > 2:
                level = int(level) / 10
            else:
                level = float(level)
        level -= 50
        spkrEnum=Channel.Centre
        if self.status[code] is None:
            self.status[code] = {}
        self.status[code][spkrEnum] = level
        if self.notifyCmd:
            if self.status[code]:
                logging.debug(f"My Channel level is now {_dict_enum_to_string(self.status[code])}")
            else:
                logging.debug(f"My Channel level is empty")
            self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])      

    def _parse_PSSWL(self, resp: str) -> None:
        cmd="SSLEV"
        code = self.CMDS_DEFS[cmd].code
        if resp.startswith("2 "):
            spkrEnum=Channel.Subwoofer2
            resp=resp[1:].strip()
        else:
            spkrEnum=Channel.Subwoofer
        level=only_int(resp)
        if level:
            if len(level) > 3:
                logging.error(f"error when parsing speaker level: level {level} is too big")        
            elif len(level) > 2:
                level = int(level) / 10
            else:
                level = float(level)
        level -= 50
        
        if self.status[code] is None:
            self.status[code] = {}
        self.status[code][spkrEnum] = level
        if self.notifyCmd:
            if self.status[code]:
                logging.debug(f"My Channel level is now {_dict_enum_to_string(self.status[code])}")
            else:
                logging.debug(f"My Channel level is empty")
            self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])      

    def _parse_PSHEQ(self, resp: str) -> None:
        self._parse_control_on_off(resp, "PSHEQ")

    def _parse_PSDYNEQ(self, resp: str) -> None:
        self._parse_control_on_off(resp, "PSDYNEQ")

    def _parse_PSREFLEV(self, resp: str) -> None:
        self._parse_int(resp, "PSREFLEV", 0, 99)
        
    def _parse_NSFRN(self, resp: str) -> None:
        self._parse_string(resp, "NSFRN")        
        
    def _parse_SSINFFRM(self, resp: str) -> None:
        cmd="SSINFFRM"
        code = self.CMDS_DEFS[cmd].code
        if resp.startswith("END"):
            return
        typeMC, resp = resp.split(" ", 1)
        try:
            typeMCEnum=MicroCodeType(typeMC)
            # logging.debug(f"Converting '{typeMC}' into enum: {typeMCEnum.name}:{typeMCEnum.value}")
        except ValueError as e:
            logging.debug(f"Unknown type {typeMC}")
            return
        resp=resp.replace("_", " ")
        resp=resp.strip()
        if self.status[code] is None:
            self.status[code] = {}
        self.status[code][typeMCEnum] = resp  
        if self.notifyCmd:
            self.notifyCmd(self, self.CMDS_DEFS[cmd], self.status[code])
           
    def _parse_SSLOC(self, resp: str) -> None:
        self._parse_control_on_off(resp, "SSLOC")
           
    #xxxxx#
            

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
                # log the cancellation
                logging.info(f'Reading task was cancelled, details: {asyncio.current_task()}')
                # re-raise the exception
                raise
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
        logging.info(f'Reading task is done')

    async def _do_write(self):
        """ Keep on reading the info coming from the AVR"""

        while self.alive:
            try:
                cmd, param = await self.write_queue.get()
                if cmd:
                    await self._send_command(cmd, param)
                self.write_queue.task_done()
                #wait 1s before sending next message. Device is not happy when too fast...
                await asyncio.sleep(1.0)
            except asyncio.CancelledError as e:
                # log the cancellation
                logging.info(f'Writing task was cancelled, details: {asyncio.current_task()}')
                # re-raise the exception
                raise
            except Exception as e:
                logging.debug("Problem processing write: {} - {}".format(e, data.decode().strip("\r")))
                logging.debug(traceback.format_exc())
        logging.info(f'Writing task is done')

    async def _do_ping(self):
        """ Send a ping to the AVR every _pingFreq s"""
        while self.alive:
            try:
                #logging.debug("Send ping ...")
                self.write_queue.put_nowait(("PW", "?"))
                if self.notifyEvent:
                    self.notifyEvent(self, EventAVR.Ping, {})                
                await asyncio.sleep(self._timeout)
                #check timeout
                delayLastMessage = time.time() - self._lastMessageTime
                logging.debug(f"Ping: Last message received {delayLastMessage:.2f}s ago")
                if delayLastMessage>self._timeout:
                    self.timeout()
                else:
                    self._timeoutCnt=0 
                await asyncio.sleep(self._pingFreq - self._timeout)                    
            except asyncio.CancelledError as e:
                # log the cancellation
                logging.info(f'Pinging task was cancelled, details: {asyncio.current_task()}')
                # re-raise the exception
                raise
            except Exception as e:
                logging.debug("Problem processing ping: {} - {}".format(e, e.__class__.__name__))  
                logging.debug(traceback.format_exc())     
        logging.info(f'Pinging task is done')
