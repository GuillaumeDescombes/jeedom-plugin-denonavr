#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# Originaly from https://github.com/silvester747/aio_marantz_avr
#
# These are messages one can receive from the device.
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

"""Enums used by the AVR."""

from enum import Enum


class Power(Enum):
    Off = "OFF"
    On = "ON"
    Standby = "STANDBY"


class Channel(Enum):
    FrontLeft = "FL"
    FrontRight = "FR"
    Centre = "C"
    Subwoofer = "SW"
    Subwoofer2 = "SW2"
    SurroundLeft = "SL"
    SurroundRight = "SR"
    SurroundBackLeft = "SBL"
    SurroundBackRight = "SBR"
    SurroundBack = "SB"
    FrontHeightLeft = "FHL"
    FrontHeightRight = "FHR"
    FrontWideLeft = "FWL"
    FronWideRight = "FWR"
    FrontTopLeft = "TFL"
    FrontTopRight = "TFR"
    MiddleTopLeft = "TML"
    MiddleTopRight = "TMR"
    RearTopLeft = "TRL"
    RearTopRight = "TRR"
    RearHeightLeft = "RHL"
    RearHeightRight = "RHR"
    FrontDolbyLeft = "FDL"
    FrontDolbyRight = "FDR"
    SurroundDolbyLeft = "SDL"
    SurroundDolbyRight = "SDR"
    BackDolbyLeft = "BDL"
    BackDolbyRight = "BDR"
    SurroundHeightLeft = "SHL"
    SurroundHeightRight = "SHR"
    TopSurround = "TS"
    CentreHeight = "CH"


class InputSource(Enum):
    Phono = "PHONO"
    CD = "CD"
    DVD = "DVD"
    Bluray = "BD"
    TV = "TV"
    SetTopBox = "SAT/CBL"
    MediaPlayer = "MPLAY"
    Game = "GAME"
    Tuner = "TUNER"
    HDRadio = "HDRADIO"
    SiriusXM = "SIRIUSXM"
    Pandora = "PANDORA"
    LastFM = "LASTFM"
    Flickr = "FLICKR"
    Spotify = "SPOTIFY"
    InternetRadio = "IRADIO"
    Server = "SERVER"
    Favourites = "FAVORITES"
    Aux1 = "AUX1"
    Aux2 = "AUX2"
    Aux3 = "AUX3"
    Aux4 = "AUX4"
    Aux5 = "AUX5"
    Aux6 = "AUX6"
    Aux7 = "AUX7"
    OnlineMusic = "NET"
    Bluetooth = "BT"
    MXPORT = "MXPORT"
    USB = "USB"
    IPODDirect = "IPOD DIRECT"
    IPOD = "IPOD"
    USBIPOD = "USB/IPOD"
    NONE = "OFF"
    MainSource = "SOURCE"
    HeightK = "8K" 


class AudioInput(Enum):
    Auto = "AUTO"
    HDMI = "HDMI"
    Digital = "DIGITAL"
    Analog = "ANALOG"
    MultiChannel = "7.1IN"
    NoSound = "NO"


class EcoMode(Enum):
    Off = "OFF"
    On = "ON"
    Auto = "AUTO"

class SurroundMode(Enum):
    # Settable values
    Movie = "MOVIE"
    Music = "MUSIC"
    Game = "GAME"
    Direct = "DIRECT"
    PureDirect = "PURE DIRECT"
    Stereo = "STEREO"
    Auto = "AUTO"
    DolbyDigital = "DOLBY DIGITAL"
    #DolbyDigitalSurround = "DOLBY DIGITAL SURROUND"
    DtsSurround = "DTS SURROUND"
    Auro3D = "AURO3D"
    Auro2DSurround = "AURO2DSURR"
    MultiChannelStereo = "MCH STEREO"
    SuperStadium = "SUPER STADIUM"
    RockArena = "ROCK ARENA"
    JazzClub = "JAZZ CLUB"
    ClassicConcert = "CLASSIC CONCERT"
    MonoMovie = "MONO MOVIE"
    Matrix = "MATRIX"
    Virtual = "VIRTUAL"

    # Rotate between options
    Left = "LEFT"
    Right = "RIGHT"


class PictureMode(Enum):
    # Settable values
    Off = "OFF"
    Standard = "STD"
    Movie = "MOV"
    Vivid = "VVD"
    Stream = "STM"
    Custom = "CTM"
    ISFDay = "DAY"
    ISFNight = "NGT"


class DRCMode(Enum):
    # Dynamic Range compression values
    Off = "OFF"
    Auto = "AUTO"
    High = "HI"
    Medium = "MID"
    Low = "LOW"

class DynamicMode(Enum):
    # Dynamic mode
    Off = "OFF"
    Day = "DAY"
    Evening = "EVE"
    Night = "NGT"
    
class DynamicVolume(Enum):
    # Dynamic volume
    Off = "OFF"
    Light = "LIT"
    Medium = "MED"
    Heavy = "HEV"
    
class Zone(Enum):
    # Zone
    UndefinedZone = "UNDEFINED"
    MainZone = "1"
    Zone2 = "2"
    Zone3 = "3"
    
class EventAVR(Enum):
    Init = "Init"
    Cmd = "Cmd"
    TimeOut = "TimeOut"
    Close = "Close"
    Ping = "Ping"
    
class Bluetooth(Enum):
    Transmitter = "Transmitter"
    OutputMode = "OutputMode"

class BluetoothTransmitter(Enum):
    Off = "OFF"
    On = "ON"
    
class BluetoothOutputMode(Enum):
    BTandSpeaker = "SP"
    BTonly = "BT"
    
class AudioRestorer(Enum):
    Off = "OFF"
    Low = "LOW"
    Med = "MED"
    Hi = "HI"
    
class SoundMode(Enum):
    Music = "MUS"
    Movie = "MOV"
    Game = "GAM"
    PureDirect = "PUR"
    
class MicroCodeType(Enum):
    DTC = "DTS"
    AVR = "AVR"
     
class Standby(Enum):
    S15M = "15M"
    S30M = "30M"
    S60M = "60M"
    Off = "OFF"
 