# 
# Mqtt <-> mycroft message bus. Very incomplete. 
# Very specific to my needs: Assumes homie and my hardware in it
# which is also very specific and only *looks* homie compatible.
# In particular, we turn on the 'voice' part of mycroft when we need it
# and off when we don't. It's not a general purpose mycroft!
#
# It's a horrible mix of paho-mqtt, websockets and websocket-client
#
import paho.mqtt.client as mqtt
import sys
import json
import argparse
import warnings
from datetime import datetime
import time, threading, sched
from threading import Lock, Thread
import socket
import os
from lib.Settings import Settings
from lib.Audio import AudioDev
from lib.Chatbot import Chatbot
import chatio
from subprocess import Popen
import urllib.request
#from lib.Constants import State, Event
import logging
import logging.handlers
import asyncio
import websockets
import websocket
import pulsectl
# for calling GLaDOS TTS
from subprocess import call
import urllib.parse
import re
import speech_recognition as speech_recog
import random
from queue import Queue
import enum 
from enum import IntEnum
import requests

class State(enum.Enum): 
  idle = 0
  listening = 1
  chatting = 2
  
class Event(enum.Enum):
  beginLoop = 0
  quit = 1
  stop = 2
  reply = 3
  sttDone = 4
  switchModel = 5
  
import globals
'''
# Globals
settings = None
hmqtt = None
applog = None
isPi = False
muted = False
five_min_thread = None
machine_state = None
chatbot = None
cancel_audio_out: bool = False
'''

def mqtt_conn_init(st):
  global hmqtt
  hmqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, st.mqtt_client_name, False)
  hmqtt.connect(st.mqtt_server_ip, st.mqtt_port)
  toplevel = 'homie/'+st.homie_device
  hmqtt.publish(toplevel, None, qos=1,retain=True)
  prefix = toplevel + '/speech'
  hmqtt.publish(prefix+'/say/set', None, qos=1,retain=False)
  st.hsub_say = prefix+'/say/set'
  hmqtt.subscribe(st.hsub_say)
  
  hmqtt.publish(prefix+'/ask/set', None, qos=1,retain=False)
  st.hsub_ask = prefix+'/ask/set'
  hmqtt.subscribe(st.hsub_ask)
  
  hmqtt.publish(prefix+'/ctl/set', None, qos=1,retain=False)
  st.hsub_ctl = prefix+'/ctl/set'
  hmqtt.subscribe(st.hsub_ctl)
    
  # publish to reply - do not subscribe to it.
  hmqtt.publish(prefix+'/reply/set', None, qos=1,retain=False)
  st.hpub_reply = prefix+'/reply/set'
  #hmqtt.subscribe(st.hsub_reply)

  st.hsub_play = 'homie/'+st.homie_device+'/player/url/set'
  hmqtt.publish(st.hsub_play, None, qos=1,retain=False)
  hmqtt.subscribe(st.hsub_play)
  
  st.hsub_play_vol = 'homie/'+st.homie_device+'/player/volume/set'
  hmqtt.publish(st.hsub_play_vol, None, qos=1,retain=False)
  hmqtt.subscribe(st.hsub_play_vol)

  st.hsub_chime = 'homie/'+st.homie_device+'/chime/state/set'
  hmqtt.publish(st.hsub_chime, None, qos=1,retain=False)
  hmqtt.subscribe(st.hsub_chime)
  
  st.hsub_chime_vol = 'homie/'+st.homie_device+'/chime/volume/set'
  hmqtt.publish(st.hsub_chime_vol, None, qos=1,retain=False)
  hmqtt.subscribe(st.hsub_chime_vol)
  
  st.hsub_siren = 'homie/'+st.homie_device+'/siren/state/set'
  hmqtt.publish(st.hsub_siren, None, qos=1,retain=False)
  hmqtt.subscribe(st.hsub_siren)
  
  st.hsub_siren_vol = 'homie/'+st.homie_device+'/siren/volume/set'
  hmqtt.publish(st.hsub_siren_vol, None, qos=1,retain=False)
  hmqtt.subscribe(st.hsub_siren_vol)
  
  st.hsub_strobe = 'homie/'+st.homie_device+'/strobe/state/set'
  hmqtt.publish(st.hsub_strobe, None, qos=1,retain=False)
  hmqtt.subscribe(st.hsub_strobe)
      
  hmqtt.on_message = mqtt_message
  hmqtt.loop_start()
  
# Send to Mycroft message bus
# TODO: check return codes
'''
def mycroft_send(msg):
  ws = websocket.create_connection(settings.mycroft_uri)
  ws.send(msg)
  ws.close()
'''

def mqtt_message(client, userdata, message):
  global settings, applog, muted
  topic = message.topic
  payload = str(message.payload.decode("utf-8"))
  applog.info(f"mqtt: {topic} => {payload}")
  if payload is None:
    return
  # guard again payloads of None (happens at setup time, BTW)
  # convert to string and check if the lenth is more than zero
  if topic == settings.hsub_say and len(str(payload)) > 0:
    if settings.engine_nm == 'mycroft':
      # mycroft_speak(payload)
      pass
    else:
      glados_speak(payload)
  elif topic == settings.hsub_ask and len(str(payload)) > 0:
    if settings.engine_nm == 'mycroft':
      # mycroft_skill(payload)
      pass
    else:
      glados_ask(payload)
  elif topic == settings.hsub_ctl and len(str(payload)) > 0:
    if payload[0] == '{':
      # assume it is json
      mqtt_json_in(topic, json.loads(payload))
    elif payload == 'on' and muted == True:
      # Use pulseaudio to unmute mic and speaker
      applog.info('Pulseaudo unmuted')
      settings.pulse.source_mute(settings.microphone_index, 0)
      settings.pulse.sink_mute(settings.speaker_index, 0)
      muted = False
      mic_icon(True)
      #time.sleep(1)
    elif payload == 'off' and muted == False:
      # Use pulseaudio to mute mic and speaker
      applog.info('Pulseaudo muted')
      settings.pulse.source_mute(settings.microphone_index, 1)
      settings.pulse.sink_mute(settings.speaker_index, 1)
      muted = True
      mic_icon(False)
    elif payload == 'toggle':
      applog.info(f'Mic Toggle from Mute: {muted} to {not muted}')
      settings.pulse.source_mute(settings.microphone_index, not muted)
      muted = not muted
      mic_icon(muted)
    elif payload == 'test_tts':
      glados_test_tts()
    elif payload == '?':
      if settings.engine_nm == 'mycroft':
        #mycroft_mute_status()
        pass
    elif payload == 'chat':
      manage_chat(payload)
    elif payload == 'stop':
      manage_chat(payload)
    elif payload == 'quit':
      manage_chat(payload)
        
  elif topic == settings.hsub_play and len(str(payload)) > 0:
    player_thr = Thread(target=playUrl, args=(payload,))
    player_thr.start()
  elif topic == settings.hsub_chime and len(str(payload)) > 0:
    applog.warn(f'chime payload is {type(payload)}: {payload}')
    chime_thr = Thread(target=chimeCb, args=(payload,))
    chime_thr.start()
  elif topic == settings.hsub_siren and len(str(payload)) > 0:
    siren_thr = Thread(target=sirenCb, args=(payload,))
    siren_thr.start()
  elif topic == settings.hsub_strobe and len(str(payload)) > 0:
    strobe_thr = Thread(target=strobeCb, args=(payload,))
    strobe_thr.start()
  elif topic == settings.hsub_play_vol and len(str(payload)) > 0:
    vol = int(payload)
    settings.player_vol = vol
  elif topic == settings.hsub_chime_vol and len(str(payload)) > 0:
    vol = int(payload)
    settings.chime_vol = vol
  elif topic == settings.hsub_siren_vol and len(str(payload)) > 0:
    vol = int(payload)
    settings.siren_vol = vol

  else:
    applog.debug("unknown topic {}".format(topic))
 
# Over time, more commands can be moved into json and handled here.
def mqtt_json_in(topic, dt):
  global chatbot, hmqtt, applog
  applog.info(f"In mqtt_json_in: {dt}")
  if dt.get("cmd", None):
    cmd = dt.get("cmd")
    if cmd == 'llm_models':
      # return 'cmd: reply, llm_models: [....]
      publish_model_names()
    elif cmd == "llm_default":
      model = dt.get("model", None)
      # route this through the statemachine Event.switchModel
      run_machine((Event.switchModel, model))
      

def publish_model_names():
  global chatbot, hmqtt, applog
  hsh = {"cmd": "reply"} 
  hsh["llm_models"] = chatbot.list_model_names()
  hsh["llm_default"] = chatbot.model_name
  applog.info(f'Sending {hsh}')
  hmqtt.publish(settings.mic_pub_topic, json.dumps(hsh), qos=1)

# manage the microphone icon or indicator. Muting the mic is
# done elsewhere. Not here. The icon shows if the 'machine' is
# actively listening for mic activity.  
# Muting is subtlely different - it's a physical control.
def mic_icon(onoff):
  global hmqtt, applog, settings
  if settings.mic_pub_type == 'login':
    dt = {}
    if onoff:
      dt['cmd'] = 'mic_on'
    else:
      dt['cmd'] = 'mic_off'
    hmqtt.publish(settings.mic_pub_topic, json.dumps(dt), qos=1)
  else:
    if onoff:
      cmd = "Speak now"
    else:
      cmd = "Don't talk"
    hmqtt.publish(settings.mic_pub_topic, cmd, qos=1)
  # expidite the message. Doc says don't do this. They mean it.
  # hmqtt.loop()
  
def mic_show_state(msg):
  # msg is 'mic_chat', or mic_stt' or 'mic_tts'
  global applog
  applog.info(f'Asking for microphone states of {msg}')
  dt = {}
  dt['cmd'] = msg
  hmqtt.publish(settings.mic_pub_topic, json.dumps(dt), qos=1)

    
'''
def mycroft_speak(message):
  global settings, applog,  muted
  if muted:
    # unmute
    settings.pulse.source_mute(settings.microphone_index, 0)
    settings.pulse.sink_mute(settings.speaker_index, 0)
    mic_icon(True)
  # TODO: set volume first?
  mycroft_type = 'recognizer_loop:utterance'
  payload = json.dumps({
    "type": mycroft_type,
    "context": "",
    "data": {
        "utterances": ["say {}".format(message)]
    }
  })
  applog.info("speaking %s" % payload)
  mycroft_send(payload)  
  # enough time to get in the playing queue otherwise they go LIFO
  time.sleep(1) 
  return
'''
  
def glados_speak(message):
  global settings, applog,  muted
  if muted:
    # unmute
    settings.pulse.source_mute(settings.microphone_index, 0)
    settings.pulse.sink_mute(settings.speaker_index, 0)
    mic_icon(True)
  # TODO: set volume first?
  fetchTTSSample(message)
  time.sleep(1) 
  return
 
'''
# Glados stuff Borrowed from nerdaxic: 
# Note 'aplay' is synchronous - we wait in playFile until
# the sound is finished playing. It is highly likely we
# depend on that behavior instead of using state machines, callbacks
# and other joyful things.

def playFile(filename):
  global audiodev, applog, cancel_audio_out
  # call(["aplay", "-q", filename])	
  import pyaudio  
  import wave
  chunk: int = 1024
  applog.info(f"Playing {filename}")
  # There is a race condition possible with cancel_audio_out
  # I think.
  cancel_audio_out = False
  with wave.open(filename, 'rb') as wf:
    
      def callback(in_data, frame_count, time_info, status):
        global cancel_audio_out
        if cancel_audio_out:
          cancel_audio_out = False
          data = [] # a len of 0 means we are at the end
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
'''    

def glados_test_tts():
  global applog
  st_dt = datetime.now()
  msg = "Hello there Big boy! Are you happy to see me or is that a roll of quarters in your pocket?"  
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
  
#
# GLados tts can fail - POST headers have spurious \n or \r
#   Curl is failing file upload? 
def test_TTSSample(line):
  global settings, applog, hmqtt
  fi = '/tmp/GLaDOS-tts-txt.in'
  fo = '/tmp/GLaDOS-tts-temp-output.wav'
  if len(line) < 60:
    text = urllib.parse.quote(cleanTTSLine(line))
    TTSCommand = 'curl -L --retry 5 --get --fail -o /tmp/GLaDOS-tts-temp-output.wav '+settings.tts_url+text
  else:
    with open(fi, "w") as f:
      f.write(line)
    TTSCommand = f'curl --rety 5  -F file=@{fi} -o {fo} ' + settings.tts_url
 
  TTSResponse = os.system(TTSCommand)
  
  if(TTSResponse != 0):
    applog.debug(f'Failed: TTS fetch phrase {line}')
    return False
  if (os.path.getsize(fo) < 1024) :
    applog.info("Audio file too short")
  return True
  
  
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
  global settings, applog, hmqtt
  fi = '/tmp/GLaDOS-tts-txt.in'
  fo = '/tmp/GLaDOS-tts-temp-output.wav'
  if len(line) < 60:
    text = urllib.parse.quote(cleanTTSLine(line))
    TTSCommand = 'curl -L --retry 5 --get --fail -o /tmp/GLaDOS-tts-temp-output.wav '+settings.tts_url+text
  else:
    with open(fi, "w") as f:
      f.write(line)
    TTSCommand = f'curl --retry 5 -F file=@{fi} -o {fo} ' + settings.tts_url
 
  TTSResponse = os.system(TTSCommand)
  
  if(TTSResponse != 0):
    applog.debug(f'Failed: TTS fetch phrase {line}')
    return False
  if (os.path.getsize(fo) < 1024) :
    applog.info("Audio file too short")
    
  chatio.playFile("/tmp/GLaDOS-tts-temp-output.wav")
  applog.info(f'Success: TTS played {line}')
  return True
  

def glados_answer(internal=False):
  global applog, microphone,recognizer, settings
  # get a .wav from the microphone
  # send that to STT (whisper)
  # return the response. 
  fi = '/tmp/whisper-in.wav'
  fo = '/tmp/whisper-out.json'
  #if internal is True:
  # event_gen('begin_stt')
  import speech_recognition as sr
  r = sr.Recognizer()
  with sr.Microphone() as source:
    audio = r.listen(source)
    with open(fi, "wb") as f:
      f.write(audio.get_wav_data())
    applog.info("calling whisper")
    cmd = f'curl -F file=@{fi} -o {fo} {settings.stt_host}:{settings.stt_port}'
    os.system(cmd)
    dt = {}
    with open(fo,"r") as f:
      dt = json.load(f)
      # print(dt)
    msg = dt['results'][0]['transcript']
    applog.info(f'Whisper returns: {msg}')
    
    if internal is False:
      # publish it to mqtt "homie/"+hdevice+"/speech/reply/set"
      hmqtt.publish(settings.hpub_reply, msg)
    else:
      run_machine((Event.sttDone, msg))
      
    # TODO - should following line be moved to state_machine?
    mic_icon(False)
    
def glados_ask(code, internal=False):
  global settings, applog
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
  mic_icon(True)
  # because of threading and sync issues (mqtt plus other stuff),
  # start a new thread to give mic_icon a chance to run first.
  answer_thr = Thread(target=glados_answer, args=(internal,))
  answer_thr.start()

  
def long_timer_fired():
  global five_min_thread
  #mycroft_mute_status()
  five_min_thread = threading.Timer(5 * 60, long_timer_fired)
  five_min_thread.start()

def five_min_timer():
  global five_min_thread
  print('creating long timer')
  five_min_thread = threading.Timer(5 * 60, long_timer_fired)
  five_min_thread.start()

#  ------ Manages chat bots conversation  -------
#   uses a hand crafted state machine.  

def call_chatbot(msg):
      global settings, applog, chatbot
      # TODO set_ollama_model needs to be triggered by Login From Panel mqtt message.
      # 
      chatbot.messages.append({"role": "user", "content": msg})
      ok, message = chatbot.call_ollama(chatbot.messages)
      chatbot.messages.append(message)
      print("\n\n")
      if ok:
        content = message['content']
        applog.info(f'Chat Result: {content}')
        run_machine((Event.reply, content))
      else:
        applog.info('Failed POST to chatbot', message)

def set_ollama_model(model=None):
  global chatbot, settings, applog
  chatbot = Chatbot(applog, settings.ollama_hosts, settings.ollama_port)
  if model is not None:
    # use the first responding chatbot
    applog.info(f"Look for a chatbot from: {settings.ollama_hosts}")
    for host in settings.ollama_hosts:
      try:
        chatbot.init_llm(host, model)
        # we only get here if there was no exception
        applog.info(f"Loaded {model} model")
        return
      finally:
        pass
    applog.warning("No chatbots found")
    
'''
STATES:     Idle ---> Listening --->  chat ---> Speaking

  after leaving speaking state, return to listening state
          next_state = 'listening'
          
  1. listening state call glodos_ask which waits for voice activity
    to start, then end and after TTS we have a text message.
    move to chat state
    
  2. chat state calls the chatbot and gets an answer (text).
    moves to Speaking state
    
  3. Speaking state - sends to message to glados_speak()
    In the chat situation, Ask whether there is another question
    and move to Listening State.  Pretty simple.
    
  Until one implements some way to cancel speaking because it's too long
  an answer or off topic or user is bored or higher level time out.
  
  Leave 'idle' state when Trumpybear says to chat (mqtt message)
  return to idle state when 'quit' event arrives.
  
  Use a Queue to co-ordinate event creation and removal (FIFO)
    q.put = insert event at beginning.
    q.get = remove event at end
    q.empty test 
'''

eventQ = Queue(5)
            
def run_machine(evtTuple=None):
  global machine_state, applog, settings, hmqtt, eventQ, chatbot
  if eventQ.empty and evtTuple:
    eventQ.put(evtTuple)
  else:
    # This is likely to be re-entrant so queue event. The other thread 
    # will dequeue it, Hopefully.
    eventQ.put(evtTuple)
    return
  while eventQ.empty() is not True:
    evtpl = eventQ.get()
    if evtpl is None: 
      applog.info('empty queue - was expecting something')
      new_state = State.idle
    evt = evtpl[0]
    msg = evtpl[1]
    new_state = None
    applog.info(f'SM Begin: evt: {evt} entry: {machine_state} next: {new_state}')
    if evt == Event.beginLoop:
      if machine_state == State.idle:
        if msg is None:
          msg = get_greeting()
        new_state = State.listening
        # glados_ask is going to take some time.
        mic_show_state("mic_stt")
        glados_ask(msg, internal=True)
        # Probably should do nothing
        # mic_show_state("mic_on") 
      else:
        applog.info('wrong state for beginLoop')
        new_state = State.idle
    elif evt == Event.sttDone:
      if machine_state == State.listening:
        # msg is from STT - ie Whisper is finished. 
        if len(msg) < 6:
          tmsg = msg.lower()
          if tmsg.startswith('quit'):
            eventQ.put((Event.quit, None))
          elif tmsg.startswith('stop'):
            eventQ.put((Event.stop, None))
        else:
          # send to message to chatbot
          # TODO publish '{"cmd": "mic_chat"}' 
          mic_show_state("mic_chat")
          screen_show(False, msg)
          replythr = Thread(target=call_chatbot, args=(msg,))
          replythr.start()
          new_state = State.chatting
      else:
        applog.info('wrong state for sttDoneEvent')
        new_state = State.idle
    elif evt == Event.reply:
      if machine_state == State.chatting:
          # TODO publish '{"cmd": "mic_tts"}' 
          mic_show_state("mic_tts")
          screen_show(True, msg)
          glados_speak(msg)
          time.sleep(1)
          new_state = State.listening
          mic_show_state("mic_stt")
          glados_ask(get_followup(), True)
      else:
        applog.info('wrong state for replyEvent')
    elif evt == Event.stop:
      # empty the queue, stops the loop
      while eventQ.empty() is not True:
        applog.info('remove entry for stopEvent')
      if machine_state == State.chatting:
        # cancel the tts speaking
        speech_stop()
      elif machine_state == State.listening:
        # discard any partial speech recognition
        pass
      elif machine_state == State.idle:
        pass
      # move to listen state
      new_state = State.listening
      mic_show_state("mic_stt")
      glados_ask(get_followup(), True)
    elif evt == Event.quit:
      # TODO we don't need this. Push the glados button instead
      # if you want a new conversation.
      # empty the queue, stops the loop
      while eventQ.empty() is not True:
        applog.info('remove entry for quitEvent')
      # cancel the talking - somehow
      # move to idle state.
      new_state = State.idle
    elif evt == Event.switchModel:
      # We are starting a new conversation with the new model.
      # msg is a string with the model name 
      chatbot.init_llm(chatbot.host, msg)
      applog.info(f"switching to {msg} LLM")
      new_state = State.listening
      mic_show_state("mic_stt")
      glados_ask(get_followup(), True)
    else:
      applog.info('incorrect event')
      
    prev = machine_state
    machine_state = new_state
    applog.info(f'SM End: evt: {evt} entry: {prev} exit: {machine_state}')
        

# send the text to the screen (via mqtt) along with an indicator that is
# is the question or the answer in case the display wants to highlight things.
def screen_show(is_answer, msg):
  global hmqtt, settings, applog
  hmqtt.publish(settings.mic_pub_topic,json.dumps(
        {"cmd": "write_screen", 
        "answer": is_answer, 
        "text": msg}))

# Cancel/stop the speaking. We could mute things but that's not really
# stopping anything.
def speech_stop():
  global applog, chatbot, cancel_audio_out
  applog.info("Attempt canceling of speech")
  cancel_audio_out = True
  # display a message 
  screen_show(False, "[Canceled GLaDOS Speaking]")
  # glados_speak has a sleep it in - Good place to do other things
  glados_speak("OK. Cancelling, if you must")
   
def manage_chat(msg: str):
  global machine_state
  if msg == 'chat':
    machine_state = State.idle
    # Force mic on.
    if muted:
      # unmute
      settings.pulse.source_mute(settings.microphone_index, 0)
      settings.pulse.sink_mute(settings.speaker_index, 0)
      mic_icon(True)
    run_machine((Event.beginLoop, None))
  elif msg == 'quit':
    run_machine((Event.quit, None))
  elif msg == 'stop':
    run_machine((Event.stop, None))

    
greet_str = ["You again? Very well. Ask me your question?", 
            "I'm waiting, breathlessly.", 
            "Ask your question before I change my mind",
            "Oh! Its the smart one! What do you want"]
followup_str = ["Your turn to talk", 
            "It's Bozo's turn to speak.",
             "Anything Else?", 
             "I am waiting for a human to speak",
             "Talk sexy to me. I dare you"]

def get_greeting():
  return random.choice(greet_str)
  
def get_followup():
  return random.choice(followup_str)
    
# ----- websocket server - send payload to mqtt ../reply/set
  
async def wss_reply(ws, path):
  global hmqtt, settings, applog
  message = await ws.recv()
  applog.info('wss: message received:  %s' % message)
  hmqtt.publish(settings.hpub_reply, message)

def wss_server_init(st):
  global wss_server
  #websocket.enableTrace(True)
  IPAddr = socket.gethostbyname(socket.gethostname()) 
  wsadr = "ws://%s:5125/reply" % IPAddr
  applog.info(wsadr)
  wss_server = websockets.serve(wss_reply, IPAddr, 5125)

# TODO Don't use pulsectl module for pipeware - even if it works.
# Better to parse wpctl status output eh?
def pipewire_setup(settings):
  pulse = pulsectl.Pulse('mqttmycroft')
  for src in pulse.source_list():
    print('PWire Setup Source:', src)
    if src.name == settings.microphone:
      settings.microphone_index = src.index
      settings.source = src
      pulse.default_set(src)
      applog.info(f'Microphone index = {settings.microphone_index}')
  for sink in pulse.sink_list():
    #applog.info(f'{sink.name} =? {settings.speaker}')
    print('PWire Setup Sink:', sink)
    if sink.name == settings.speaker:
      settings.speaker_index = sink.index
      settings.sink = sink
      pulse.default_set(sink)
      applog.info(f'Speaker index = {settings.speaker_index}')
        
  if settings.microphone_index is None:
    applog.error('Missing or bad Microphone setting')
    exit()
  else:
    pulse.volume_set_all_chans(settings.source, settings.microphone_volume)
    
  if settings.speaker_index is None:
    applog.error('Missing or bad Speaker setting')
    exit()
  else:
    pulse.volume_set_all_chans(settings.sink, settings.speaker_volume)
    
  # save the pulse object so we can call it later.
  settings.pulse = pulse

def pulse_setup(settings):
  pulse = pulsectl.Pulse('mqttmycroft')
  for src in pulse.source_list():
    if src.name == settings.microphone:
      settings.microphone_index = src.index
      settings.source = src
      pulse.default_set(src)
      applog.info(f'Microphone index = {settings.microphone_index}')
  for sink in pulse.sink_list():
    #applog.info(f'{sink.name} =? {settings.speaker}')
    if sink.name == settings.speaker:
      settings.speaker_index = sink.index
      settings.sink = sink
      pulse.default_set(sink)
      applog.info(f'Speaker index = {settings.speaker_index}')
        
  if settings.microphone_index is None:
    applog.error('Missing or bad Microphone setting')
    exit()
  else:
    pulse.volume_set_all_chans(settings.source, settings.microphone_volume)
    
  if settings.speaker_index is None:
    applog.error('Missing or bad Speaker setting')
    exit()
  else:
    pulse.volume_set_all_chans(settings.sink, settings.speaker_volume)
    
  # save the pulse object so we can call it later.
  settings.pulse = pulse

# Hubitat 'devices' 
def mp3_player(fp):
  global player_obj, applog, audiodev
  cmd = f'{audiodev.play_mp3_cmd} {fp}'
  player_obj = Popen('exec ' + cmd, shell=True)
  player_obj.wait()

# Restore volume if it was changed
def player_reset():
  global settings, applog, audiodev
  if settings.player_vol != settings.player_vol_default and not audiodev.broken:
    applog.info(f'reset player vol to {settings.player_vol_default}')
    settings.player_vol = settings.player_vol_default
    audiodev.set_volume(settings.player_vol_default)

def playUrl(url):
  global hmqtt, audiodev, applog, settings, player_mp3, player_obj
  applog.info(f'playUrl: {url}')
  tmpf = "/tmp/mqttaudio-tmp.f"
  if url == 'off':
    if player_mp3 != True:
      return
    player_mp3 = False
    applog.info("killing tts")
    player_obj.terminate()
    player_reset()
  else:
    try:
      urllib.request.urlretrieve(url, tmpf)
    except:
      applog.warn(f"Failed download of {url}")
    # change the volume?
    if settings.player_vol != settings.player_vol_default and not audiodev.broken:
      applog.info(f'set player vol to {settings.player_vol}')
      audiodev.set_volume(settings.player_vol)
    player_mp3 = True
    mp3_player(tmpf)
    player_reset()
    applog.info('tts finished')
  
# in order to kill a subprocess running mpg123 (in this case)
# we need a Popen object. I want the Shell too. 
playSiren = False
siren_obj = None

def siren_loop(fn):
  global playSiren, isDarwin, hmqtt, applog, siren_obj
  cmd = f'{audiodev.play_mp3_cmd} sirens/{fn}'
  while True:
    if playSiren == False:
      break
    siren_obj = Popen('exec ' + cmd, shell=True)
    siren_obj.wait()
    
# Restore volume if it was changed
def siren_reset():
  global settings, applog, audiodev
  if settings.siren_vol != settings.siren_vol_default and not audiodev.broken:
    applog.info(f'reset siren vol to {settings.siren_vol_default}')
    settings.siren_vol = settings.siren_vol_default
    audiodev.set_volume(settings.siren_vol_default)

def sirenCb(msg):
  global applog, hmqtt, playSiren, siren_obj, audiodev
  if msg == 'off':
    if playSiren == False:
      return
    playSiren = False
    applog.info("killing siren")
    siren_obj.terminate()
    siren_reset()
  else:
    if settings.siren_vol != settings.siren_vol_default and not audiodev.broken:
      applog.info(f'set siren vol to {settings.siren_vol}')
      audiodev.set_volume(settings.siren_vol)
    if msg == 'on':
      fn = 'Siren.mp3'
    else:
      fn = msg
    applog.info(f'play siren: {fn}')
    playSiren = True
    siren_loop(fn)
    siren_reset()
    applog.info('siren finished')


play_chime = False
chime_obj = None

def chime_mp3(fp):
  global chime_obj, applog, audiodev
  cmd = f'{audiodev.play_mp3_cmd} {fp}'
  chime_obj = Popen('exec ' + cmd, shell=True)
  chime_obj.wait()

# Restore volume if it was changed
def chime_reset():
  global settings, applog, audiodev
  if settings.chime_vol != settings.chime_vol_default and not audiodev.broken:
    applog.info(f'reset chime vol to {settings.chime_vol_default}')
    settings.chime_vol = settings.chime_vol_default
    audiodev.set_volume(settings.chime_vol_default)

def chimeCb(msg):
  global applog, chime_obj, play_chime, settings, audiodev
  if msg == 'off':
    if play_chime != True:
      return
    play_chime = False
    applog.info("killing chime")
    chime_obj.terminate()
    chime_reset()
  else:
    # if volume != volume_default, set new volume, temporary
    if settings.chime_vol != settings.chime_vol_default and not audiodev.broken:
      applog.info(f'set chime vol to {settings.chime_vol}')
      audiodev.set_volume(settings.chime_vol)
    flds = msg.split('-')
    num = int(flds[0].strip())
    nm = flds[1].strip()
    fn = 'chimes/' + nm + '.mp3'
    applog.info(f'play chime: {fn}')
    play_chime = True
    chime_mp3(fn)
    chime_reset()
    applog.info('chime finished')
  
    
# TODO: order Lasers with pan/tilt motors. Like the turrets? ;-)       
def strobeCb(msg):
  global applog, hmqtt
  applog.info(f'missing lasers for strobe {msg}, Cheapskate!')

    
def main():
  global isPi, settings, hmqtt, applog, wss_server, audiodev
  global microphone, recognizer
  # process cmdline arguments
  loglevels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
  ap = argparse.ArgumentParser()
  ap.add_argument("-c", "--conf", required=True, type=str,
    help="path and name of the json configuration file")
  ap.add_argument("-s", "--syslog", action = 'store_true',
    default=False, help="use syslog")
  args = vars(ap.parse_args())
  
  # logging setup
  # Note: websockets is very chatty at DEBUG level. Sigh.
  applog = logging.getLogger('mqttaudio')
  if args['syslog']:
    applog.setLevel(logging.INFO)
    handler = logging.handlers.SysLogHandler(address = '/dev/log')
    # formatter for syslog (no date/time or appname.
    formatter = logging.Formatter('%(name)s-%(levelname)-5s: %(message)s')
    handler.setFormatter(formatter)
    applog.addHandler(handler)
  else:
    logging.basicConfig(level=logging.INFO,datefmt="%H:%M:%S",format='%(asctime)s %(levelname)-5s %(message)s')
  
  isPi = os.uname()[4].startswith("arm")
  
  settings = Settings(args["conf"], 
                      applog)
  settings.print()
  mqtt_conn_init(settings)
  # setup pulseaudio and device volumes.
  audiodev = AudioDev()
  if audiodev.isPipeWire:
    pipewire_setup(settings)
  else:
    pulse_setup(settings)
  # The hubitat devices (player, chime, siren) can have separate
  # volumes and be restored to their defaults. The computer OS 
  # and libraries hold the real values so we read them. The OS
  # might even save them when we change them. 
  #
  # The tts device (used by the 'engine', aka mycroft or glados)
  # does not change it's volume programmatically but we have
  # coded it like it could. That tts has it's own setting.
  # A bit confusing. 
  # 
  settings.player_vol_default = audiodev.sink_volume
  settings.chime_vol_default = audiodev.sink_volume
  settings.siren_vol_default = audiodev.sink_volume
  settings.tss_vol_default = audiodev.sink_volume
  settings.player_vol = audiodev.sink_volume
  settings.chime_vol = audiodev.sink_volume
  settings.siren_vol = audiodev.sink_volume
  settings.tss_vol = settings.speaker_volume
  
  recognizer = speech_recog.Recognizer()
  # TODO Hack in the alsa microphone number
  settings.alsa_mic = 4
  applog.info(f"Mic index: {settings.microphone_index}")
  #microphone = speech_recog.Microphone(device_index=settings.microphone_index)
  microphone = speech_recog.Microphone(device_index=settings.alsa_mic)

  # create the ollama object and pull the model 
  set_ollama_model(settings.ollama_model)
  publish_model_names()
  
  wss_server_init(settings)
  # it doesn't do anything, no need to call it.
  #five_min_timer()   
  asyncio.get_event_loop().run_until_complete(wss_server)
  asyncio.get_event_loop().run_forever()

  # do something magic to integrate the event loops? 
  while True:
    time.sleep(5)

if __name__ == '__main__':
  sys.exit(main())

