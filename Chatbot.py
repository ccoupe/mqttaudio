# Class for ollama chatbot connections and context management
# for me, Ollama is likely to be running under docker.
#

# import requests
# import json
from ollama import Client
# import globals
# import wave
# import time
# import sys
import os
# import pyaudio
import speechio
import re


class Chatbot:
  def __init__(self, applog, hosts, port, speechio):
    self.messages = []
    self.log = applog
    self.hosts = hosts
    self.host = None
    self.port = port
    self.client = None
    self.model_name = None
    self.models = []
    self.details = {}
    self.stream = False
    self.md_format = None
    self.delete_thinking = True
    self.prompt = None
    self.skip_to_audible = False
    self.cancel_audio_out: bool = False

  def init_llm(self, host, model_settings):
    """ model is a dict (from settings toml) that has the processing
    hints for the model we want.
    """
    model_name = model_settings['name']
    self.host = host
    self.client = Client(host=f'http://{host}:{self.port}')
    self.chat_url = f'http://{host}:{self.port}/api/chat'
    self.ollama_url = self.chat_url
    # start a new conversation with the ollama server
    self.messages = []
    dt = self.client.list()
    # self.log.info(f'Have these models: {dt}')
    self.models = dt['models']
    self.log.info(f'Have these models: {self.models}')
    for mdl in self.models:
      if type(mdl) is not dict:
        # API change from dict to (class ?)
        self.log.info(f"new: {mdl.model} is type {type(mdl)}")
      else:
        self.log.info(f"Have: dict {mdl['name']}")
    
    self.model_name = None
    for mdl in self.models:
      if type(mdl) == dict and mdl['name'] == model_name:
        self.model_name = model_name
        break
      elif mdl.model == model_name:
        self.log.info(f"matched {mdl}")
        self.model_name = model_name
        break
    
    # if we don't have that model, pull it
    if self.model_name is None:
      self.model_name = model_name
      self.log.info(f"Pulling {self.model_name} model")
      self.client.pull(model=self.model_name)
      
    # for good luck, get the 'show' contents
    self.details = self.client.show(self.model_name)
    self.details['license'] = None  # There can be too much info
    self.log.info(f'{self.model_name} Details: {self.details}')
    
    # now process our settings for model_settings, for now these are
    # instance variables
    # TODO It is not appropriate to crash if these are not found
    self.stream = model_settings.get('stream', None)
    self.md_format = model_settings['md_format']
    self.delete_thinking = model_settings["delete_think_blocks"]
    self.prompt = model_settings.get("prompt", None)
    self.skip_to_audible = model_settings["use_audible_tag"]
    
  def list_models(self):
    return self.client.list()

  def list_model_names(self):
    mdlnm = []
    for mdl in self.models:
      if type(mdl) is dict:
        mdlnm.append(mdl['name'])
      else:
        mdlnm.append(mdl.model)
    return mdlnm

  def default_prompt(self, mdl: str, prefix: str):
    # please, no colons in filename
    if mdl is None:
      filename = self.model_name.split(':')[0]
    else:
      filename = mdl.split(':')[0]
    promptf = f"prompts/{prefix}-{filename}.prompt"
    if not os.path.exists(promptf):
      with open(promptf, "w") as f:
        f.write("You are GlaDOS from the game Portal. You are terse, coy and \
snarky, by default.\nYou are connected to a text to speech device so limit \
your output to text you want the user to hear audibly.\nDo not output your \
chain of thought or reasoning.")
    return promptf
    
  # Use the streaming, non-rest Python API.
  def call_ollama(self, messages):
    self.log.info(f"Calling chat, using {self.model_name} model")
    if self.stream is False:
      # return call_ollama_nostream(self, messages)
      response = self.client.chat(model=self.model_name,
                                  messages=messages,
                                  stream=False)
      self.log.info('Back from ollama non-stream chat()')
      alltext = response['message']['content']
      self.log.info(f'RAW CHAT RESPONSE: {alltext}')
      inthink = False
      # havaudible = False
      newlines = []
      skipped = []
      for ln in alltext.splitlines():
        if ln.startswith("<think>") and self.delete_thinking:
          inthink = True
        if ln.startswith("</think>") and self.delete_thinking:
          inthink = False
          continue
        if not inthink:
          newlines.append(ln)
        else:
          skipped.append(ln)
      alltext = "\n".join(newlines)
      self.log.info(f"AFTER THINK CHECK: {alltext}")
      self.log.info(f"SKIPPED {len(skipped)} LINES")
      speechio.enqueTTS(alltext)
      tks = 0.0
      if response.get('done', False):
        if response.get('eval_count', False) and response.get('eval_duration', False):
          tks = response['eval_count'] / response['eval_duration'] * 10.0e9
          self.log.info(f'tokens/sec: {tks}')
      return tks, alltext
      
    if messages is None:
      self.log.info("call_ollama: Messages should not be null")
      return False, []
    stream = self.client.chat(model=self.model_name,
                              messages=messages,
                              stream=True)
    self.log.info('Back from ollama chat()')
    alltext = ""
    flatstr = ""
    tks = 0.0
    for chunk in stream:
      done = chunk['done']
      if done is True:
        if chunk.get('eval_count', False) and chunk.get('eval_duration', False):
          tks = chunk['eval_count'] / chunk['eval_duration'] * 10e9
        break
      content = chunk['message']['content']
      # print("c ", content)
      if content.endswith("\n\n"):
        # We have a paragraph separator
        # does the buffer have text to flush?
        if len(flatstr) > 0:
          # print("p ", flatstr, end="\n\n", flush=True)
          # enque flatstring to be converted (TTS) and wav file enqued in
          # the play queue trigger deque of play queue if nothing is playing
          #
          # TODO better way to remove think tags
          flatstr = re.sub(r"<think>.*?</think>\n?", '', flatstr)
          speechio.enqueTTS(flatstr)
        else:
          # print("e ", content, end="", flush=True)
          pass
        flatstr = ""
        alltext += "\n\n"
      else:
        flatstr += str(content)
        alltext += str(content)
    
    return tks, alltext
  
