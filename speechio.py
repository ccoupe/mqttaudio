# Module for speechio functions and part of Trumpybear.
#
# This probably not useful for standalone usage - but who knows.
import globals
import wave
import time
import sys
import os
import json
import pyaudio
import speech_recognition as sr
from lib.Constants import State, Event
import urllib.parse
import re
from threading import Lock, Thread

# In this module are
#  playFile(filename: str) -> None:
#  answer(internal: bool =False) -> None: # NOTE tied to MQTT
#  speak(message: str) -> None:
#  ask(code: str, internal: bool=False)
#  test_tts() -> None:

# globals in this module:
cancel_audio_out: bool = False

def stop_audio(flag: bool=True):
  global cancel_audio_out

def playFile(filename: str) -> None:
  global cancel_audio_out
  chunk: int = 1024
  globals.applog.info(f"Playing {filename}")
  #
  # I think there could be a race condition possible with cancel_audio_out
  # 
  cancel_audio_out = False
  with wave.open(filename, 'rb') as wf:
    
      def callback(in_data, frame_count, time_info, status):
        if globals.cancel_audio_out:
          globals.cancel_audio_out = False
          data = [] # a len of 0 means we are at the end
          #return (data, pyaudio.paAbort)
          return (data, pyaudio.paComplete)
        else:
          data = wf.readframes(frame_count)
        # If len(data) is less than requested frame_count, PyAudio automatically
        # assumes the stream is finished, and the stream stops.
        return (data, pyaudio.paContinue)

      # Instantiate PyAudio and initialize PortAudio system resources (1)
      p = pyaudio.PyAudio()
  
      # Open stream (2)
      stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                      channels=wf.getnchannels(),
                      rate=wf.getframerate(),
                      output=True,
                      stream_callback=callback)
  
      # Wait for stream to finish (4)
      while stream.is_active():
          time.sleep(0.1)
      
      # Close the stream (5)
      stream.close()
      
      # Release PortAudio system resources (6)
      p.terminate()

def answer(internal: bool =False) -> None:
  #global applog, microphone,recognizer, settings
  # get a .wav from the microphone
  # send that to STT (whisper)
  # return the response. 
  fi = '/tmp/whisper-in.wav'
  fo = '/tmp/whisper-out.json'
  
  r = sr.Recognizer()
  with sr.Microphone() as source:
    audio = r.listen(source)
    with open(fi, "wb") as f:
      f.write(audio.get_wav_data())
    globals.applog.info("calling whisper")
    cmd = f'curl -F file=@{fi} -o {fo} {globals.settings.stt_host}:{globals.settings.stt_port}'
    os.system(cmd)
    dt = {}
    with open(fo,"r") as f:
      dt = json.load(f)
      # print(dt)
    msg = dt['results'][0]['transcript']
    globals.applog.info(f'Whisper returns: {msg}')
    
    if internal is False:
      # publish it to mqtt "homie/"+hdevice+"/speech/reply/set"
      globals.hmqtt.publish(globals.settings.hpub_reply, msg)
      # set the microphone icon to off state
      globals.hmqtt.publish(globals.settings.mic_pub_topic, 
                            json.dumps({"cmd": "mic_off"}),qos=1)
    else:
      globals.run_machine((Event.sttDone, msg))
      

def speak(message: str) -> None:
  #global settings, applog,  muted
  if globals.muted:
    # unmute
    globals.settings.pulse.source_mute(globals.settings.microphone_index, 0)
    globals.settings.pulse.sink_mute(globals.settings.speaker_index, 0)
    # mic_icon(True)
    globals.hmqtt.publish(globals.settings.mic_pub_topic, 
                            json.dumps({"cmd": "mic_on"}),qos=1)
    
  # TODO: set volume first?
  fetchTTSSample(message)
  time.sleep(1) 
  return
  
# Turns units etc into speakable text
def cleanTTSLine(line):
  #line = line.replace("sauna", "incinerator")
  line = line.replace("'", "")
  line = line.lower()
  
  if re.search("-\d", line):
    line = line.replace("-", "negative ")
  
  return line

# Get GLaDOS TTS 
def fetchTTSSample(line):
  #global settings, applog, hmqtt
  fi = '/tmp/GLaDOS-tts-txt.in'
  fo = '/tmp/GLaDOS-tts-temp-output.wav'
  if len(line) < 60:
    text = urllib.parse.quote(cleanTTSLine(line))
    TTSCommand = 'curl -L --retry 5 --get --fail -o /tmp/GLaDOS-tts-temp-output.wav '+globals.settings.tts_url+text
  else:
    with open(fi, "w") as f:
      f.write(line)
    TTSCommand = f'curl --retry 5 -F file=@{fi} -o {fo} ' + globals.settings.tts_url
 
  TTSResponse = os.system(TTSCommand)
  
  if(TTSResponse != 0):
    globals.applog.debug(f'Failed: TTS fetch phrase {line}')
    return False
  if (os.path.getsize(fo) < 1024) :
    globals.applog.info("Audio file too short")
    
  playFile("/tmp/GLaDOS-tts-temp-output.wav")
  globals.applog.info(f'Success: TTS played {line}')
  return True
 
def ask(code: str, internal: bool=False):
  #global settings, applog
  # some messages from trumpybear are mycroft codes. Glados needs to
  # ask the appropriate question.
  if code == 'nameis':
    msg = "Hello sweety! Tell me your name."
  elif code == 'music_talk':
    msg = 'I could play you a favorite tune of mine or we could \
have a conversation. Say music or talk. Pick wisely. Music or Talk?'
  else:
    msg = code
  # speak our prompt msg. Zero length messages are a feature.
  if len(msg) > 0:
    fetchTTSSample(msg)
  # because of threading and sync issues (mqtt plus other stuff),
  # start a new thread to give other things a chance to run.
  answer_thr = Thread(target=answer, args=(internal,))
  answer_thr.start()

#
# GLados tts can fail - POST headers have spurious \n or \r
#   Curl is failing file upload? 
def test_TTSSample(line):
  #global settings, applog, hmqtt
  fi = '/tmp/GLaDOS-tts-txt.in'
  fo = '/tmp/GLaDOS-tts-temp-output.wav'
  if len(line) < 60:
    text = urllib.parse.quote(cleanTTSLine(line))
    TTSCommand = 'curl -L --retry 5 --get --fail -o /tmp/GLaDOS-tts-temp-output.wav '+globals.settings.tts_url+text
  else:
    with open(fi, "w") as f:
      f.write(line)
    TTSCommand = f'curl --rety 5  -F file=@{fi} -o {fo} ' + globals.settings.tts_url
 
  TTSResponse = os.system(TTSCommand)
  
  if(TTSResponse != 0):
    globals.applog.debug(f'Failed: TTS fetch phrase {line}')
    return False
  if (os.path.getsize(fo) < 1024) :
    globals.applog.info("Audio file too short")
  return True

def test_tts() -> None:
  #global applog
  st_dt = datetime.now()
  msg = "Hello there Big boy! Are you happy to see me or is that a roll of quarters in your pocket?"  
  test_TTSSample(msg)
  end_dt = datetime.now()
  globals.applog.info(f'Begin mesg 1: {st_dt} Finished: {end_dt}')
  st_dt = end_dt
  test_TTSSample(msg)
  end_dt = datetime.now()
  applog.info(f'Begin mesg 2: {st_dt} Finished: {end_dt}')
  # Cause a failure - somewhere down the line their should be a complaint
  globals.applog.info("Cause a failure")
  test_TTSSample("")
  globals.applog.info("TSS failure above? Please?")
