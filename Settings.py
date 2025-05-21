import json
import os
import socket
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


class Settings:

  def __init__(self, etcf, log):
    self.etcfname = etcf
    self.log = log
    self.hostname = socket.gethostname().split(".")[0]
    if etcf.endswith('.toml'):
      self.load_toml(self.etcfname)
      self.log.info("Toml Settings from %s" % self.etcfname)
    else:
      # self.load_settings(self.etcfname)
      self.log.info("JSON Settings from %s" % self.etcfname)
      
  def load_toml(self, config_file):
    if not os.path.exists(config_file):
      raise FileNotFoundError(f"toml file not found: {config_file}")
    try:
      with open(config_file, 'rb') as f:
        conf = tomllib.load(f)
        # print(conf)
        # [mqtt] section
        try:
          mqtt = conf['mqtt']
          self.mqtt_server_ip = mqtt.get("mqtt_server_ip", "192.168.1.2")
          self.mqtt_port = mqtt.get("mqtt_port", 1883)
          self.mqtt_client_name = mqtt.get("mqtt_client_name", "trumpy_bridge")
          self.homie_device = mqtt.get('homie_device', 'trumpy_cam')
          self.bridge_ip = mqtt.get('bridge_ip', '192.168.1.2')
          self.bridge_port = mqtt.get('bridge_port', 8281)
        except (RuntimeError, NameError):
          raise "Missing mqtt section?"
          
        # [tts] section
        try:
          tts = conf['tts']
          self.engine_nm = tts.get("engine", None)
          self.engine_name = tts[self.engine_nm]
          self.tts_url = self.engine_name['tts_url']
          if self.engine_name == 'glados2':
            self.audio_api = 'openai'
          else:
            self.audio_api = None
          # print(f"tts: {engine_nm} -> {self.tts_url}")
        except (RuntimeError, NameError):
          raise "Missing tts section?"

        # [microphone] section
        try:
          mic = conf['microphone']
          micselect = mic['microphone']
          self.microphone = mic[micselect]
          self.microphone_volume = mic.get('microphone_volume', 0.60)
          self.microphone_pyaudio = mic.get("microphone_pyaudio _name", "pulse")
          self.microphone_index = None
          self.mic_pub_type = mic.get('mic_pub_type', 'notify')  # or 'login'
          self.mic_pub_topic = mic.get('mic_pub_topic',
                                       'homie/pi4_screen/screen/display/text/set')
          self.alsa_mic = None
          self.pulse = None  # TODO Not used/needed?
          print(f'microphone: {self.microphone} vol: {self.microphone_volume}')
        except (RuntimeError, NameError):
          raise "Missing microphone section?"

        # [speaker] section
        try:
          spk = conf['speaker_section']
          spktyp = spk.get('speaker', None)
          self.speaker = spk.get(spktyp, None)
          self.speaker_volume = spk.get('speaker_volume', 0.50)
          print(f"Speaker {self.speaker} vol: {self.speaker_volume}")
        except (RuntimeError, NameError):
          raise "Missing speaker section?"
          
        # [ollama] section
        # historically ollama_models was a dictionary
        try:
          ollama = conf['ollama']
          self.ollama_hosts = ollama.get('ollama_hosts', None)
          self.ollama_port = ollama.get("ollama_port", 11434)
          models = ollama["ollama_models"]
          self.ollama_default_model = ollama.get("ollama_default_model", None)
          # print(f'llm host: {self.ollama_hosts}:{self.ollama_port} using'
          # f' {self.ollama_default_model}')
        except (RuntimeError, NameError):
          raise "Missing ollama section?"
        self.ollama_models = {}
        self.ollama_models[self.ollama_default_model] = models
        
        # [stt] section
        try:
          stt = conf.get('stt', None)
          self.stt_host = stt.get('stt_host', 'bronco.local')
          self.stt_port = stt.get('stt_port', 5003)
          # print(f'STT: {self.stt_host}:{self.stt_port}')
        except (RuntimeError, NameError):
          raise "Missing stt section?"
                
    except Exception as e:
      raise RuntimeError(f"An unexpected error occurred while loading toml: {e}")

  def load_settings(self, config_file):
    # conf = json.load(open(fn))
    if not os.path.exists(config_file):
      raise FileNotFoundError(f"json file not found: {config_file}")
    try:
      with open(config_file, 'r') as f:
        conf = json.load(f)
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
        self.ollama_hosts = conf.get("ollama_hosts", [])
        self.ollama_port = conf.get("ollama_port", 11434)
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
    except json.JSONDecodeError as e:
      raise ValueError(f"Error decoding JSON in {config_file}: {e}")
    except Exception as e:
      raise RuntimeError(f"An unexpected error occurred while loading json: {e}")

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
    # st['mycroft_uri'] = self.mycroft_uri
    st['tts_url'] = self.tts_url
    str = json.dumps(st)
    return str

  def settings_deserialize(self, jsonstr):
    json.loads(jsonstr)
