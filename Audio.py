#!/usr/bin/env python3

# a word about volumes.
# Hubitat says 0 to 100 with separate mute/unmute commands, up/down commands
#   don't specify step size. use 5 (aka 5% of 100)
# OSX volume goes from 0 to 100 - 0 is mute
# PulseAudio is 0..65536 or nnn% (80%) or +/-n.f db
#  we use the nn%
# Alsa here means raspberry w/o pulseaudo. It might work on other Alsa
#   systems w/o pulseaudo. I wouldn't depend on it though.
#   Alsa provides nn% so we use that. alsamixer is confusing about this.
# Pipewire - sigh. The code assumes that pactl works - ie pulseaudio
#   bridge to Pipewire is setup and working. Like on a Raspberry pi running
#   Bookworm. I should do something with wpctl - I can get info easier and it
#   would not depend on pactl.
#   80 means 80% or as pipewire perfers 0.80. We scale to the integer number - yes
#   in can go higher, up to 150.

import sys
import os
from os import path
import re
import json


class AudioDev:

  def __init__(self):
    self.isLinux = sys.platform.startswith("linux")
    self.isDarwin = sys.platform.startswith("darwin")
    self.isAlsa = False
    self.isPulse = False
    self.isPipeWire = False
    self.sink_dev = None
    self.sink_idx = None
    self.sink_volume = None  # 0..100
    self.source_dev = None
    self.broken = False
    self.play_mp3_cmd = ''
    self.play_wav_cmd = ''
    if self.isLinux:
      # print("Linux")
      if self.findPipeWire():
        self.isPipeWire = True
        self.pipewire_config()
        self.play_mp3_cmd = 'mpg123 -q --no-control'
        self.play_wav_cmd = 'pw_play'
      elif self.findPulse():
        self.isPulse = True
        self.pulse_config()
        self.play_mp3_cmd = 'mpg123 -q --no-control'
        self.play_wav_cmd = 'paplay'
        # print(f'sink: {self.sink_idx} {self.sink_dev} {self.sink_volume}')
      else:
        self.isAlsa = True
        self.play_mp3_cmd = 'mpg123 -q --no-control'
        self.play_wav_cmd = 'aplay -q'
        self.alsa_config()
        # print(f'sink: {self.sink_idx} {self.sink_dev} {self.sink_volume}')
    if self.isDarwin:
      self.osx_config()
      self.play_mp3_cmd = 'afplay'
      self.play_wav_cmd = 'afplay'
      # print(f'sink: {self.sink_idx} {self.sink_dev} {self.sink_volume}')
      
  def osx_config(self):
    # get current volume
    val = os.popen("osascript -e 'output volume of (get volume settings)'",
                   mode='r').readlines()
    for v in val:
      self.sink_volume = int(v)
      # print(f'vol: {int(v)}')
    self.sink_dev = 'system'
    self.sink_idx = 0

  # --------------- PipeWire --------------------------
  
  def findPipeWire(self):
    if path.exists('/usr/bin/pw-cli'):
      return True
    return False
    
  def pipewire_withpulse_config(self):
    lines = os.popen('pw-dump -N', mode='r').readlines()
    bigstr = ''
    for ln in lines:
      bigstr = bigstr + ln
    dt = json.loads(bigstr)
    for ent in dt:
      if ent['id'] == 35:
        mlist = ent['metadata']
        for li in mlist:
          # find 'key': 'default.configured.audio.sink'
          if li['key'] == 'default.configured.audio.sink':
            val = li['value']
            self.sink_dev = val['name']
            # print("Our Sink:", self.sink_dev)
            self.sink_volume = self.pulse_getvol()
            # print(f"Our Sink is {self.sink_dev} volume: {self.sink_volume}")

  def pipewire_config(self):
    in_audio = False
    in_video = False
    in_settings = False
    in_audio_sinks = False
    lines = os.popen('wpctl status', mode='r').readlines()
    for ln in lines:
      ln = ln.strip()
      if ln == 'Audio':
        in_audio = True
        in_video = False
        in_settings = False
        continue
      elif ln == 'Video':
        in_audio = False
        in_video = True
        in_settings = False
        continue
      elif ln == 'Settings':
        in_audio = False
        in_video = False
        in_settings = True
        continue
        
      if in_audio:
        continue
      elif in_audio_sinks:
        print('Have', len(ln), ln)
        in_audio_sinks = False
        continue
      elif in_video:
        continue
      elif in_settings:
        flds = ln.split(' ')
        if flds[1] == 'Audio/Sink':
          self.sink_dev = flds[-1]
        elif flds[1] == 'Audio/Source':
          self.source_dev = flds[-1]

    self.sink_volume = self.pipewire_getvol()
    
  def pipewire_getvol(self):
    lines = os.popen('wpctl get-volume @DEFAULT_AUDIO_SINK@', mode='r').readlines()
    for ln in lines:
      ln = ln.strip()
      if len(ln) > 8:
        flds = ln.split(' ')
        vol = float(flds[1]) * 100
        print('@VOLUME@', vol)
        return vol
            
  # ------------ PulseAudio ---------

  def findPulse(self):
    if path.exists('/usr/bin/pulseaudio'):
      # print('Pulse')
      return True
    return False
    
  def pulse_config(self):
    lines = os.popen('pacmd stat', mode='r').readlines()
    for ln in lines:
      ln = ln.strip()
      if ln.startswith('Default sink'):
        flds = ln.split(' ')
        self.sink_dev = flds[3]
        print('default', self.sink_dev)
        break
    try:
      self.sink_volume = self.pulse_getvol()
    except:
      self.broken = True
      # running as root may not accesss pulseaudio. Sigh.
      print('Pulse and root permissions?')
    
  def pulse_getvol(self):
    sinks = {}
    sink = 0
    sinkn = ''
    lines = os.popen('pactl list sinks', mode='r').readlines()
    for ln in lines:
      ln = ln.strip()
      if ln.startswith('Sink #'):
        sink = int(ln[6:])
      if ln.startswith('Name:'):
        sinkn = ln[6:]
      if ln.startswith('Volume:'):
        t = ln[8:]
        m = re.match(r'front-left: (\d+)\s/\s+(\d+)%\s/\s(.+)\sdB,(.*)', t)
        if m is not None:
          val = int(m.group(1))
          per = int(m.group(2))
          db = float(m.group(3))
          sinks[sinkn] = {'idx': sink, 'vol': (val, per, db)}
          if sinkn == self.sink_dev:
            # print('found default', sinks[sinkn])
            break
        else:
          # expect failures that don't matter i.e. 'mono'
          # print(f'Failed regex for {t}')
          pass
          
    # print(sinkn, sinks[self.sink_dev])
    d = sinks[self.sink_dev]
    self.sink_idx = d['idx']
    # use % value
    tv = d['vol'][1]
    return int(tv)
    
  def alsa_config(self):
    lns = os.popen('amixer', mode='r').readlines()
    for ln in lns:
      m = re.match(r"Simple mixer control '(.*)',(\d)", ln)
      if m is not None:
        self.sink_dev = m.group(1)
        self.sink_idx = m.group(2)  # not useful
      else:
        pass
    lns = os.popen('amixer controls', mode='r').readlines()
    for ln in lns:
      ln = ln.strip()
      m = re.match(r'numid=(\d+),iface=MIXER,name=\'(\w+) Playback Volume\'', ln)
      if m is not None:
        if m.group(2) == self.sink_dev:
          self.sink_idx = m.group(1)
      else:
        # print('miss:',ln)
        pass
    self.sink_volume = self.alsa_getvol()

  def alsa_getvol(self):
    lns = os.popen('amixer', mode='r').readlines()
    for ln in lns:
      ln = ln.strip()
      m = re.match(r'.*\[(\d+)%\]', ln)
      if m:
        # print('found', m.group(1))
        # on Pi this is the only one. Not so on others, but first one
        # is usually 'Master' which is what we need
        return int(m.group(1))
        
  def get_volume(self):
    # get from the system/pulse/alsa system. slower than reading the property
    # Still it's useful for checking
    if self.isDarwin:
      val = os.popen("osascript -e 'output volume of (get volume settings)'",
                     mode='r').readlines()
      for v in val:
        self.sink_volume = int(v)
    elif self.isPipeWire:
      self.sink_volume = self.pipewire_getvol()
    elif self.isPulse:
      self.sink_volume = self.pulse_getvol()
    elif self.isAlsa:
      self.sink_volume = self.alsa_getvol()
    else:
      raise Exception("unknown sound system")
    return self.sink_volume
       
  def set_volume(self, amt):
    if amt < 0 or amt > 150:
      raise ValueError
    self.sink_volume = amt
    if self.isDarwin:
      os.system(f'osascript -e "set volume output volume {self.sink_volume}"')
    elif self.isPipeWire:
      tv = self.sink_volume
      os.system(f'wpctl set-volume @DEFAULT_AUDIO_SINK@ {tv / 100.0}')
    elif self.isPulse:
      tv = self.sink_volume
      os.system(f'pactl set-sink-volume {self.sink_dev} {tv}%')
    elif self.isAlsa:
      os.popen(f'amixer cset numid={self.sink_idx} {self.sink_volume}%',
               mode='r').readlines
    else:
      raise Exception("unknown sound system")

   
if __name__ == '__main__':
  # a little test program
  ad = AudioDev()
  print('output to:', ad.sink_dev)
  pv = ad.get_volume()
  print('cur vol:', pv)
  # ad.set_volume(60)
  ad.set_volume(120)
  print('new vol:', ad.sink_volume, ad.get_volume())
  ad.set_volume(pv)
  print('rst vol:', ad.sink_volume, ad.get_volume())
