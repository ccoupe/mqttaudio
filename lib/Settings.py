#!/usr/bin/env python3
import json
# import socket
# from uuid import getnode as get_mac
# import os
# import sys


class Settings:

  def __init__(self, etcf, log):
    self.etcfname = etcf
    self.log = log
    self.load_settings(self.etcfname)
    self.log.info("Settings from %s" % self.etcfname)
    
  def load_settings(self, fn):
    conf = json.load(open(fn))
    self.mqtt_server_ip = conf.get("mqtt_server_ip", "192.168.1.7")
    self.mqtt_port = conf.get("mqtt_port", 1883)
    self.mqtt_client_name = conf.get("mqtt_client_name", "trumpy_bridge")
    self.homie_device = conf.get('homie_device', 'trumpy_cam')
    self.pulse = None
    self.microphone = conf.get('microphone', None)
    self.microphone_volume = conf.get('microphone_volume', 0.5)
    self.microphone_pyaudio = conf.get("microphone_pyaudio _name", "pulse")
    self.microphone_index = None
    self.alsa_mic = None
    self.speaker = conf.get('speaker', None)
    self.speaker_volume = conf.get('speaker_volume', 0.5)
    self.speaker_index = None
    self.spkr = None
    self.bridge_ip = conf.get('bridge_ip', '192.168.1.2')
    self.bridge_port = conf.get('bridge_port', 8281)
    self.engine_nm = conf.get("engine", None)
    self.engine_nm = conf.get("tts_engine", self.engine_nm)	 # newer name
    # self.ollama_urls = conf.get("ollama_urls", ['not found'])
    # self.ollama_pulls = conf.get("ollama_pulls",['not found'])
    self.ollama_hosts = conf.get("ollama_hosts", [])
    self.ollama_port = conf.get("ollama_port", 11434)
    # self.ollama_model = conf.get("ollama_model", "llama2-uncensored:7b")
    # self.ollama_sys_prompt = conf.get("sys_prompt", "prompt.txt")
    self.ollama_models = conf.get("ollama_models", None)
    self.ollama_default_model = conf.get("ollama_default_model",
                                         "stablelm-zephyr:latest")
    engine_dt = conf.get(self.engine_nm, {})
    self.tts_url = engine_dt.get('tts_url', None)
    
    self.mic_pub_type = conf.get('mic_pub_type', 'notify')  # or 'login'
    self.mic_pub_topic = conf.get('mic_pub_topic',
                                  'homie/pi4_screen/screen/display/text/set')
    # its required that the bridge runs on the mycroft device (if mycroft)
    # because it likes to manage pulseaudio (and alsa) too.
    self.mycroft_uri = 'ws://' + self.bridge_ip + ':8181/core'
    self.stt_host = conf.get('stt_host', 'bronco.local')
    self.stt_port = conf.get('stt_port', 5003)

  def print(self):
    self.log.info("==== Settings ====")
    self.log.info(self.settings_serialize())
  
  def settings_serialize(self):
    st = {}
    st['mqtt_server_ip'] = self.mqtt_server_ip
    st['mqtt_port'] = self.mqtt_port
    st['mqtt_client_name'] = self.mqtt_client_name
    st['homie_device'] = self.homie_device
    st['bridge_ip'] = self.bridge_ip
    st['bridge_port'] = self.bridge_port
    st['mycroft_uri'] = self.mycroft_uri
    st['tts_url'] = self.tts_url
    str = json.dumps(st)
    return str

  def settings_deserialize(self, jsonstr):
    json.loads(jsonstr)
