# Module for speechio functions and part of Trumpybear.
#
# This probably not useful for standalone usage - but who knows.
import gvars
import wave
import time
# import sys
import os
import json
import pyaudio
import speech_recognition as speech_recog
from lib.Constants import Event
# from lib.Settings import Settings
import urllib.parse
import re
from threading import Lock, Thread
# import logging
from queue import Queue
import tempfile
import datetime
# from subprocess import Popen

# In this module are
#  playFile(filename: str) -> None:
#  answer(internal: bool =False) -> None: # NOTE tied to MQTT
#  speak(message: str) -> None:
#  ask(code: str, internal: bool=False)
#  test_tts() -> None:

# TODO - Not needed?
gvars.cancel_audio_out = False


def enqueTTS(msg):
  # This bad boy sets up a lot of concurrent things.
  if gvars.tts_queue is None:
    gvars.tts_queue = Queue()
  if gvars.tts_thread is None:
    gvars.tts_thread = Thread(target=dequeTTS, daemon=True)
    gvars.tts_thread.start()
  if gvars.play_queue is None:
    gvars.play_queue = Queue()
  if gvars.play_thread is None:
    gvars.play_thread = Thread(target=dequePlay, daemon=True)
    gvars.play_thread.start()
  if gvars.play_lock is None:
    gvars.play_lock = Lock()

  gvars.applog.info(f'enqueueTTS()  called, msg len = {len(msg)}: {msg}')
  # replace double asteriks ** and other LLM helpfulness that doesn't
  # sound well when spoken. maybe.
  text = cleanTTSLine(msg)
  # create a temp file pathname for the .wav to be written to
  fo = tempfile.mkstemp(prefix='glados-', suffix='.wav')
  fopname = fo[1]
  gvars.applog.info(f"fopname = {fopname}")
  # Queue up that text msg and and the temp path and enter it at the end
  # of the TTS queue. That will cause the thread to process any queued entries
  # including when the file has be created it will be placed on the playQueue
  if gvars.settings.engine_nm == 'glados2':
    # just pass text strings to TTS
    dt = {}
    dt['input'] = text
    dt['model'] = 'Tacotron'
    dt['voice'] = 'GlaDOS'
    gvars.tts_queue.put((dt, fopname))
  else:
	  # create a temp file pathname for the msg and write msg to it.
	  fi = tempfile.mkstemp(prefix='glados-', suffix='.txt', text=True)
	  fipname = fi[1]
	  fil = open(fipname, mode="w")
	  fil.write(text)
	  fil.close()	  
	  gvars.tts_queue.put((fipname, fopname))
 
 
# This is the thread that processes the tts_queue.
#
def dequeTTS():
  while True:
    # get the next entry (a tuple) from the Queue
    ent = gvars.tts_queue.get()
    fpin = ent[0]
    fpon = ent[1]
    if isinstance(fpin, dict): 
      # version 2 settings.audio_api=='openai' > True. 
      # fpin is not a file name string
      jstr = json.dumps(fpin)
      tts_cmd = (f'curl -H "Authorization: Bearer not-needed"'
                f' -H "Content-Type: application/json" -d \'{jstr}\''
                f' -o {fpon} ') + gvars.settings.tts_url
      gvars.applog.info(f'tts queue: create {fpon} from {fpin}')
      gvars.applog.info(f'ttscmd: {tts_cmd}')
      tts_resp = os.system(tts_cmd)
      
    else:
      # print(f'gvars.applog={gvars.applog}')
      gvars.applog.info(f'tts queue: create {fpon} from {fpin}')
      tts_cmd = f'curl --retry 5 -F file=@{fpin} -o {fpon} ' + gvars.settings.tts_url
      tts_resp = os.system(tts_cmd)
  
    # TODO Make exceptions for below conditions
    if tts_resp != 0:
      gvars.applog.debug(f'Failed: TTS fetch {tts_resp}')
      return False
    if os.path.getsize(fpon) < 1024:
      gvars.applog.info("Audio file too short")
      return False
      
    # Now, enter the wav file name into the play que.
    gvars.play_queue.put(fpon)
    # signal the end of the tts/curl task
    gvars.tts_queue.task_done()

  
def stop_audio(flag: bool = True):
  gvars.cancel_audio_out = True
  # clean out the queues and threads
  # shutdown not available in python < 3.13
  # gvars.tts_queue.shutdown(immediate=True)
  # gvars.tts_thread.stop()
  try:
    while not gvars.tts_queue.empty():
      gvars.tts_queue.get(False)
      gvars.tts_queue.task_done()
  except Queue.Empty:
    gvars.tts_thread = Thread(target=dequeTTS, daemon=True)
    gvars.tts_thread.start()

  # play_queue
  # gvars.play_queue.shutdown(immediate=True)
  # gvars,play_thread.stop()
  try:
    while not gvars.play_queue.empty():
      gvars.play_queue.get(False)
      gvars.play_queue.task_done()
  except Queue.Empty:
    gvars.play_thread = Thread(target=dequeTTS, daemon=True)
    gvars.play_thread.start()
  
 
def dequePlay():
  while True:
    fin = gvars.play_queue.get()
    gvars.play_lock.acquire()
    gvars.applog.info(f'starting play of {fin} depth {gvars.play_queue.qsize()}')
    # syncPlayFile(fin)
    playFile(fin)
    gvars.applog.info(f'ending play of {fin}')
    gvars.play_lock.release()
    gvars.play_queue.task_done()
    if gvars.play_queue.empty():
      gvars.applog.info('empty play queue')
      gvars.run_machine((Event.end_speaking, None))


def syncPlayFile(filename: str) -> None:
  chunk = 1024
  gvars.applog.info(f"Playing {filename}")
  with wave.open(filename, 'rb') as wf:
      # Instantiate PyAudio and initialize PortAudio system resources (1)
      p = pyaudio.PyAudio()
      
      # Open stream (2)
      stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                      channels=wf.getnchannels(),
                      rate=wf.getframerate(),
                      output=True)
      # read data (based on the chunk size)
      data = wf.readframes(chunk)
      # play stream (looping from beginning of file to the end)
      while data:
        # writing to the stream is what *actually* plays the sound.
        stream.write(data)
        data = wf.readframes(chunk)
      
      # Close the stream (5)
      stream.close()
      
      # Release PortAudio system resources (6)
      p.terminate()
    

def playFile(filename: str) -> None:
  # chunk: int = 1024
  gvars.applog.info(f"Playing {filename}")
  #
  # I think there could be a race condition possible with cancel_audio_out
  #
  gvars.cancel_audio_out = False
  with wave.open(filename, 'rb') as wf:
    
      def callback(in_data, frame_count, time_info, status):
        if gvars.cancel_audio_out:
          gvars.cancel_audio_out = False
          data = []  # a len of 0 means we are at the end
          # return (data, pyaudio.paAbort)
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


def answer(internal: bool = False) -> None:
  global settings
  # get a .wav from the microphone
  # send that to STT (whisper)
  # return the response.
  fi = '/tmp/whisper-in.wav'
  fo = '/tmp/whisper-out.json'
  
  r = speech_recog.Recognizer()
  '''
  gvars.microphone = speech_recog.Microphone(
    device_index=gvars.settings.alsa_mic)
  '''
  with speech_recog.Microphone(device_index=gvars.settings.alsa_mic) as source:
    gvars.microphone = source
    audio = r.listen(source)
    with open(fi, "wb") as f:
      f.write(audio.get_wav_data())
    gvars.applog.info("calling whisper")
    cmd = f'curl -F file=@{fi} -o {fo} {gvars.settings.stt_host}:\
{gvars.settings.stt_port}'
    os.system(cmd)
    dt = {}
    with open(fo, "r") as f:
      dt = json.load(f)
      # print(dt)
    msg = dt['results'][0]['transcript']
    gvars.applog.info(f'Whisper returns: {msg}')
    
    if internal is False:
      # publish it to mqtt "homie/"+hdevice+"/speech/reply/set"
      gvars.hmqtt.publish(gvars.settings.hpub_reply, msg)
      # set the microphone icon to off state
      gvars.hmqtt.publish(gvars.settings.mic_pub_topic,
                          json.dumps({"cmd": "mic_off"}), qos=1)
    else:
      gvars.run_machine((Event.sttDone, msg))
      

def speak(message: str) -> None:
  if gvars.muted:
    # unmute
    gvars.settings.pulse.source_mute(gvars.settings.microphone_index, 0)
    gvars.settings.pulse.sink_mute(gvars.settings.speaker_index, 0)
    # mic_icon(True)
    gvars.hmqtt.publish(gvars.settings.mic_pub_topic,
                        json.dumps({"cmd": "mic_on"}), qos=1)
    
  # TODO: set volume first?
  # fetchTTSSample(message)
  enqueTTS(message)
  time.sleep(1)
  return
  
  
# Turns units etc into speakable text
def cleanTTSLine(line):
  # line = line.replace("sauna", "incinerator")
  line = line.replace("'", "")
  line = line.lower()
  line = re.sub(r'\*\*(.+)\*\*', r'Item, \1', line)
  # if re.search("-\d", line):
  if re.search("-\\d", line):
    line = line.replace("-", "negative ")
  return line


# Get GLaDOS TTS
def fetchTTSSample(line):
  fi = '/tmp/GLaDOS-tts-txt.in'
  fo = '/tmp/GLaDOS-tts-temp-output.wav'
  if len(line) < 60:
    text = urllib.parse.quote(cleanTTSLine(line))
    print(f'gvars.applog={gvars.applog}')
    gvars.applog.info(f'short msg: {text}')
    TTSCommand = 'curl -L --retry 5 --get --fail -o \
/tmp/GLaDOS-tts-temp-output.wav ' + gvars.settings.tts_url + text
  else:
    with open(fi, "w") as f:
      f.write(line)
    TTSCommand = f'curl --retry 5 -F file=@{fi} -o {fo} ' + gvars.settings.tts_url

  TTSResponse = os.system(TTSCommand)
  
  if TTSResponse != 0:
    gvars.applog.debug(f'Failed: TTS fetch phrase {line}')
    return False
  if os.path.getsize(fo) < 1024:
    gvars.applog.info("Audio file too short")
    
  # playFile("/tmp/GLaDOS-tts-temp-output.wav")
  syncPlayFile("/tmp/GLaDOS-tts-temp-output.wav")
  gvars.applog.info(f'Success: TTS played {line}')
  return True
 
 
def ask(code: str, internal: bool = False):
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
  global settings, applog, hmqtt
  fi = '/tmp/GLaDOS-tts-txt.in'
  fo = '/tmp/GLaDOS-tts-temp-output.wav'
  if len(line) < 60:
    text = urllib.parse.quote(cleanTTSLine(line))
    TTSCommand = 'curl -L --retry 5 --get --fail -o \
/tmp/GLaDOS-tts-temp-output.wav ' + gvars.settings.tts_url + text
  else:
    with open(fi, "w") as f:
      f.write(line)
    TTSCommand = f'curl --rety 5  -F file=@{fi} -o {fo} ' + gvars.settings.tts_url
 
  TTSResponse = os.system(TTSCommand)
  
  if TTSResponse != 0:
    applog.debug(f'Failed: TTS fetch phrase {line}')
    return False
  if os.path.getsize(fo) < 1024:
    applog.info("Audio file too short")
  return True


def test_tts() -> None:
  global applog
  st_dt = datetime.now()
  msg = "Hello there Big boy! Are you happy to see me or is that a roll \
of quarters in your pocket?"
  test_TTSSample(msg)
  end_dt = datetime.now()
  applog.info(f'Begin mesg 1: {st_dt} Finished: {end_dt}')
  st_dt = end_dt
  test_TTSSample(msg)
  end_dt = datetime.now()
  applog.info(f'Begin mesg 2: {st_dt} Finished: {end_dt}')
  # Cause a failure - somewhere down the line their should be a complaint
  applog.info("Cause a failure")
  test_TTSSample("")
  applog.info("TSS failure above? Please?")
