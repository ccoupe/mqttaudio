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
import httpcore
import sys
import json
import argparse
# from datetime import datetime
import time
import threading
from threading import Thread
import socket
# import os
from Settings import Settings
from Audio import AudioDev
from Chatbot import Chatbot
# Fix the alsa 'error' message by importing sounddevice. Don't know why.
# import sounddevice
import speechio
from subprocess import Popen
import urllib.request
from Constants import State, Event
import logging
import logging.handlers
import asyncio
import websockets
# import websocket
import pulsectl
# import re
import speech_recognition as speech_recog
import random
from queue import Queue
# import requests
import gvars

# Global variables for all files
# These need global statements when referenced in a function/method
machine_state = None
five_min_thread = None
settings = None
applog = None
hmqtt = None
# These 'variables' are in gvars.py - module scope
'''
recognizer = None
microphone = None
run_machine = None
muted = False
chatbot = None
'''


def mqtt_conn_init(st):
  global hmqtt
  hmqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, st.mqtt_client_name, False)
  hmqtt.connect(st.mqtt_server_ip, st.mqtt_port)
  toplevel = 'homie/' + st.homie_device
  hmqtt.publish(toplevel, None, qos=1, retain=True)
  prefix = toplevel + '/speech'
  hmqtt.publish(prefix + '/say/set', None, qos=1, retain=False)
  st.hsub_say = prefix + '/say/set'
  hmqtt.subscribe(st.hsub_say)
  
  hmqtt.publish(prefix + '/ask/set', None, qos=1, retain=False)
  st.hsub_ask = prefix + '/ask/set'
  hmqtt.subscribe(st.hsub_ask)
  
  hmqtt.publish(prefix + '/ctl/set', None, qos=1, retain=False)
  st.hsub_ctl = prefix + '/ctl/set'
  hmqtt.subscribe(st.hsub_ctl)
  applog.info(f'Subscribed to {st.hsub_ctl}')
    
  # publish to reply - do not subscribe to it.
  hmqtt.publish(prefix + '/reply/set', None, qos=1, retain=False)
  st.hpub_reply = prefix + '/reply/set'
  # hmqtt.subscribe(st.hsub_reply)

  st.hsub_play = 'homie/' + st.homie_device + '/player/url/set'
  hmqtt.publish(st.hsub_play, None, qos=1, retain=False)
  hmqtt.subscribe(st.hsub_play)
  
  st.hsub_play_vol = 'homie/' + st.homie_device + '/player/volume/set'
  hmqtt.publish(st.hsub_play_vol, None, qos=1, retain=False)
  hmqtt.subscribe(st.hsub_play_vol)

  st.hsub_chime = 'homie/' + st.homie_device + '/chime/state/set'
  hmqtt.publish(st.hsub_chime, None, qos=1, retain=False)
  hmqtt.subscribe(st.hsub_chime)
  
  st.hsub_chime_vol = 'homie/' + st.homie_device + '/chime/volume/set'
  hmqtt.publish(st.hsub_chime_vol, None, qos=1, retain=False)
  hmqtt.subscribe(st.hsub_chime_vol)
  
  st.hsub_siren = 'homie/' + st.homie_device + '/siren/state/set'
  hmqtt.publish(st.hsub_siren, None, qos=1, retain=False)
  hmqtt.subscribe(st.hsub_siren)
  
  st.hsub_siren_vol = 'homie/' + st.homie_device + '/siren/volume/set'
  hmqtt.publish(st.hsub_siren_vol, None, qos=1, retain=False)
  hmqtt.subscribe(st.hsub_siren_vol)
  
  st.hsub_strobe = 'homie/' + st.homie_device + '/strobe/state/set'
  hmqtt.publish(st.hsub_strobe, None, qos=1, retain=False)
  hmqtt.subscribe(st.hsub_strobe)
      
  hmqtt.on_message = mqtt_message
  hmqtt.loop_start()


def mqtt_message(client, userdata, message):
  global settings, applog
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
      speechio.speak(payload)
  elif topic == settings.hsub_ask and len(str(payload)) > 0:
    if settings.engine_nm == 'mycroft':
      # mycroft_skill(payload)
      pass
    else:
      speechio.ask(payload)
  elif topic == settings.hsub_ctl and len(str(payload)) > 0:
    if payload[0] == '{':
      # assume it is json
      mqtt_json_in(topic, json.loads(payload))
    elif payload == 'on' and gvars.muted is True:
      # Use pulseaudio to unmute mic and speaker
      applog.info('Pulseaudo unmuted')
      settings.pulse.source_mute(settings.microphone_index, 0)
      settings.pulse.sink_mute(settings.speaker_index, 0)
      gvars.muted = False
      mic_icon(True)
      # time.sleep(1)
    elif payload == 'off' and gvars.muted is False:
      # Use pulseaudio to mute mic and speaker
      applog.info('Pulseaudo muted')
      settings.pulse.source_mute(settings.microphone_index, 1)
      settings.pulse.sink_mute(settings.speaker_index, 1)
      gvars.muted = True
      mic_icon(False)
    elif payload == 'toggle':
      applog.info(f'Mic Toggle from Mute: {gvars.muted} to {not gvars.muted}')
      settings.pulse.source_mute(settings.microphone_index, not gvars.muted)
      gvars.muted = not gvars.muted
      mic_icon(gvars.muted)
    elif payload == 'test_tts':
      speechio.test_tts()
    elif payload == '?':
      if settings.engine_nm == 'mycroft':
        # mycroft_mute_status()
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
    subcmd = dt.get("cmd")
    if subcmd == 'llm_models':
      # return 'cmd: reply, llm_models: [....]
      publish_model_names()
    elif subcmd == 'reply':
      applog.info('mqtt_json_in: ignore our reply')
    elif subcmd == "llm_default":
      # does this get or set default?
      # CJC: As of 4/10/2025 it 'sets'
      model = dt.get("model", None)
      # route this through the statemachine Event.switchModel?
      run_machine((Event.stop, None))
      run_machine((Event.switchModel, model))
    else:
      applog.info(f'mqtt_json_in: ignore subcmd {subcmd}')
      

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


def long_timer_fired():
  global five_min_thread
  # mycroft_mute_status()
  five_min_thread = threading.Timer(5 * 60, long_timer_fired)
  five_min_thread.start()


def five_min_timer():
  global five_min_thread
  # print('creating long timer')
  five_min_thread = threading.Timer(5 * 60, long_timer_fired)
  five_min_thread.start()


#  ------ Manages chat bots conversation  -------
#   uses a hand crafted state machine.
def call_chatbot(msg):
  global settings, applog, chatbot
  if chatbot.messages is None or len(chatbot.messages) <= 0:
    chatbot.messages = []
    if chatbot.prompt is None:
      # well hell. This can happen with tblogin switching models.
      # clean up the name string so it can be a file name
      promptf = chatbot.default_prompt(None, settings.homie_device)
    else:
      promptf = chatbot.prompt
    try:
      with open(promptf, "r") as f:
        sys_prompt = f.read()
        chatbot.messages.append({"role": "system", "content": sys_prompt})
        applog.info(f"setting system prompt to '{sys_prompt}'")
    except Exception:
      raise RuntimeError(f"Problem with {promptf} - does it exist?")
  
  chatbot.messages.append({"role": "user", "content": msg})
  tks, message = chatbot.call_ollama(chatbot.messages)
  # Really should have call_ollama return the []
  chatbot.messages.append({'content': message, 'role': "assistant"})
  print("\n\n")
  if tks > 0.0:
    applog.info(f'Chat Result: {tks} {message}')
    run_machine((Event.reply, message))
  else:
    applog.info('Failed POST to chatbot', message)


def set_ollama_model(mdl_name: str):
  """ Verify that the model in settings.ollama_default_model exists at
  the host(one of the servers listed).
  
  self.ollama_default_model is the NAME (a string) of the current model to use
  Initially that comes from a entry in the json config file.
  It can be changed by the Gui via a drop down list widget.
  The model name is used to get the corresponding model object and its
  attributes. If the model attributes don't exist, we'll have to default them
  """
  global chatbot, settings, applog
  chatbot = Chatbot(applog, settings.ollama_hosts, settings.ollama_port, speechio)
  if (mdl_name is not None):
    settings.ollama_default_model = mdl_name
  model = settings.ollama_models.get(settings.ollama_default_model, None)
  if model is None:
    # make up defaults
    promptf = chatbot.default_prompt(mdl_name, settings.homie_device)
    model = {"name": mdl_name, 'stream': True, "md_format": True,
             "delete_think_blocks": False,
             "use_audible_tag": False,
             "prompt": promptf}
    settings.ollama_models[mdl_name] = model
  # use the first responding chatbot
  applog.info(f"Look for a chatbot from: {settings.ollama_hosts}")
  for host in settings.ollama_hosts:
    try:
      chatbot.init_llm(host, model)
      # we only get here if there was no exception
      applog.info(f"Loaded {model} model from {host}")
      return
    except httpcore.ConnectError:
      continue
    finally:
      pass
  applog.warning("No chatbots found")
  # Throw an exception
  raise httpcore.ConnectError("Chatbots unreachable")


'''
STATES:     Idle ---> Listening --->  chat ---> Speaking --> followup

  after leaving speaking state, return to listening state
          next_state = 'listening'
  0. Idle state: move to listening state when the microphone button is
    pushed or the wake word is detected or trumpybear and mqtt says to.
          
  1. Listening state:  call ask() which waits for voice activity
    to start and then to end. It calls whisper to do the STT.
    Now we have a text message. If it is 'bye, 'goodbye', quit' or'stop'
    Then speak the 'bye' and move to Idle state. Else move to chat state.
    
  2. Chat state calls the chatbot and gets an answer (text).
    moves to Speaking state
    
  3. Speaking state - sends to message to speak() for tts (GlaDOS voice)
  
  4. Followup state - Speaks a prompt for the next question
    and moves to Listening State.  Note: if there is not a response
    the idle timer will fire and it moves from listening to idle.
    
  Pressing the stop button, aka mqtt {"cmd": "stop"} has to stop the speech
  if in Speaking state.
  If in chat state - we have to set a flag that the chat response code can check
  so that if set DO NOT return the message/answer AND move to followup state
  when the message is complete (vs moving to speak state)
  
  Leave 'idle' state when Trumpybear says to chat (mqtt message)
  return to idle state when 'quit' event arrives.
  
  Use a Queue to co-ordinate event creation and removal (FIFO)
    q.put = insert event at beginning.
    q.get = remove event at end
    q.empty test
    
  ========= Apr 6, 2024 ========
  One possible enhancement is to start talking when a paragraph has been
  produced from the LLM (via token streaming).
  When a paragraph has been received put it in a queue for tts to process.
  Repeat - enqueuing paragraphs.
  
  Dequeue runs in a separate thread. started/unfrozen whenever the queue has something
  in it (until empty).
  
  Sadly, it might not improve response times all that much - or even be
  noticable.
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
        # ask is going to take some time. notify fron panel process.
        panel_show_state(State.listening)
        speechio.ask(msg, internal=True)
      else:
        applog.info('wrong state for beginLoop')
        panel_show_state(State.idle)
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
          screen_show(False, msg)
          # TODO Time delay?
          panel_show_state(State.chatting)
          new_state = State.chatting
          replythr = Thread(target=call_chatbot, args=(msg,))
          replythr.start()
      else:
        applog.info('wrong state for sttDoneEvent')
        panel_show_state(State.idle)
        new_state = State.idle
    elif evt == Event.reply:
      if machine_state == State.chatting:
          panel_show_state(State.speaking)
          screen_show(True, msg)
          new_state = State.speaking
          time.sleep(1)
          # speak_thr = Thread(target=speechio.speak, args=(msg,))
          # speak_thr.start()
      else:
        applog.info('wrong state for reply Event')
    elif evt == Event.end_speaking:
      if machine_state == State.speaking:
          panel_show_state(State.listening)
          new_state = State.listening
          time.sleep(1)
          speechio.ask(get_followup(), True)
      else:
        applog.info('wrong state for end_speaking Event')
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
      panel_show_state(State.listening)
      speechio.ask(get_followup(), True)
    elif evt == Event.switchModel:
      # We are starting a new conversation with the new model.
      # msg is a string with the model name
      if machine_state == State.chatting:
        speech_stop()
      if msg != settings.ollama_default_model:
        applog.info(f"switching to {msg} LLM")
        set_ollama_model(msg)
        new_state = State.listening
        panel_show_state(State.listening)
        speechio.ask(get_followup(), True)
    else:
      applog.info('incorrect event')
      
    prev = machine_state
    machine_state = new_state
    applog.info(f'SM End: evt: {evt} entry: {prev} exit: {machine_state}')
    
    
def panel_show_state(st: State) -> None:
  hmqtt.publish(settings.mic_pub_topic, json.dumps(
                {"cmd": "bridge_machine",
                 "state": st.value}))


# runs in a thread, calls into statemachine when finished.
def speech_start():
  speechio.speak(msg)
  run_machine((Event.end_speaking, None))


# send the text to the screen (via mqtt) along with an indicator that is
# is the question or the answer in case the display wants to highlight things.
def screen_show(is_answer, msg):
  global hmqtt, settings, applog
  hmqtt.publish(settings.mic_pub_topic, json.dumps(
                {"cmd": "write_screen",
                 "answer": is_answer,
                 "text": msg}))


# Cancel/stop the speaking. We could mute things but that's not really
# stopping anything.
def speech_stop():
  applog.info("Attempt canceling of speech")
  speechio.stop_audio(True)
  # display a message
  screen_show(False, "[GLaDOS Speaking Canceled]")
  speechio.speak("OK. Cancelling, if you must")
  # we need time for the OK message to finish before we speak again,
  time.sleep(0.5)
   
   
def manage_chat(msg: str):
  global machine_state
  if msg == 'chat':
    machine_state = State.idle
    # Force mic on.
    if gvars.muted:
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
  # websocket.enableTrace(True)
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
    # applog.info(f'{sink.name} =? {settings.speaker}')
    print('PWire Setup Sink:', sink)
    if sink.name == settings.speaker:
      settings.speaker_index = sink.index
      settings.sink = sink
      pulse.default_set(sink)
      applog.info(f'Speaker index = {settings.speaker_index}')
        
  if settings.microphone_index is None:
    applog.error('Pipewire: Missing or bad Microphone setting')
    exit()
  else:
    pulse.volume_set_all_chans(settings.source, settings.microphone_volume)
    
  if settings.speaker_index is None:
    applog.error('Pipewire: Missing or bad Speaker setting')
    exit()
  else:
    pulse.volume_set_all_chans(settings.sink, settings.speaker_volume)
    
  # save the pulse object so we can call it later.
  settings.pulse = pulse


def pulse_setup(settings):
  pulse = pulsectl.Pulse('mqttmycroft')
  for src in pulse.source_list():
    applog.info(f'Pulse Source {src}')
    if src.name == settings.microphone:
      settings.microphone_index = src.index
      settings.source = src
      pulse.default_set(src)
      applog.info(f'Microphone index = {settings.microphone_index}')
  for sink in pulse.sink_list():
    applog.info(f'{sink.name} =? {settings.speaker}')
    if sink.name == settings.speaker:
      settings.speaker_index = sink.index
      settings.sink = sink
      pulse.default_set(sink)
      applog.info(f'Speaker index = {settings.speaker_index}')
        
  if settings.microphone_index is None:
    applog.error('Pulse: Missing or bad Microphone setting')
    exit()
  else:
    pulse.volume_set_all_chans(settings.source, settings.microphone_volume)
    
  if settings.speaker_index is None:
    applog.error('Pulse: Missing or bad Speaker setting')
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
    if player_mp3 is not True:
      return
    player_mp3 = False
    applog.info("killing tts")
    player_obj.terminate()
    player_reset()
  else:
    try:
      urllib.request.urlretrieve(url, tmpf)
    except Exception as e:
      applog.warn(f"Failed download of {url} {e}")
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
    if playSiren is False:
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
    if playSiren is False:
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
    if play_chime is not True:
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
    # num = int(flds[0].strip())
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
  global settings, hmqtt, applog, wss_server, audiodev
  # global microphone, recognizer
  # process cmdline arguments
  # loglevels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
  ap = argparse.ArgumentParser()
  ap.add_argument("-c", "--conf", required=True, type=str,
                  help="path and name of the json configuration file")
  ap.add_argument("-s", "--syslog", action='store_true',
                  default=False, help="use syslog")
  args = vars(ap.parse_args())
  
  # logging setup
  # Note: websockets is very chatty at DEBUG level. Sigh.
  applog = logging.getLogger('mqttaudio')
  if args['syslog']:
    applog.setLevel(logging.INFO)
    handler = logging.handlers.SysLogHandler(address='/dev/log')
    # formatter for syslog (no date/time or appname.
    formatter = logging.Formatter('%(name)s-%(levelname)-5s: %(message)s')
    handler.setFormatter(formatter)
    applog.addHandler(handler)
  else:
    logging.basicConfig(level=logging.INFO, datefmt="%H:%M:%S",
                        format='%(asctime)s %(levelname)-5s %(message)s')
  
  gvars.applog = applog
  # isPi = os.uname()[4].startswith("arm")
  settings = Settings(args["conf"],
                      applog)
  gvars.settings = settings
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
  
  applog.info(f"Checking for {settings.microphone_pyaudio} tts microphone")
  gvars.recognizer = speech_recog.Recognizer()
  # Get the Alsa microphone index for the pyaudio microphone in the json settings.
  settings.alsa_mic = -1
  mic = speech_recog.Microphone()
  applog.info(f"speech_recog.Microphone is {mic}")
  for i, microphone_name in enumerate(mic.list_microphone_names()):
    applog.info(f"have alsa {i} ==> {microphone_name}")
    if microphone_name == settings.microphone_pyaudio:
      applog.info(f'Found {settings.microphone_pyaudio}')
      settings.alsa_mic = i
  applog.info(f"Mic index: {settings.alsa_mic} for {settings.microphone_pyaudio}")
  gvars.microphone = speech_recog.Microphone(device_index=settings.alsa_mic)
  
  # TODO Eventually, I'll regret this setup for global variables.
  gvars.applog = applog
  gvars.hmqtt = hmqtt
  gvars.settings = settings
  gvars.run_machine = run_machine
  gvars.muted = False
  # gvars.chatbot = None
  gvars.cancel_audio_out: bool = False
  gvars.settings = settings
  
  # create the ollama object and pull the model (settings.default)
  set_ollama_model(None)  # use default from settings file
  publish_model_names()
  
  wss_server_init(settings)
  # it doesn't do anything, no need to call it.
  # five_min_timer()
  asyncio.get_event_loop().run_until_complete(wss_server)
  asyncio.get_event_loop().run_forever()

  # do something magic to integrate the event loops?
  while True:
    time.sleep(5)


if __name__ == '__main__':
  sys.exit(main())
