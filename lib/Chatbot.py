# Class for ollama chatbot connections and context management
# for me, Ollama is likely to be running under docker. 
#

import requests
import json
from ollama import Client
import globals
import wave
import time
import sys
import os
import pyaudio

class Chatbot:
  def __init__(self, applog, hosts, port):
    self.messages = []
    self.log = applog
    self.hosts = hosts
    self.host = None
    self.port = port
    self.client = None
    self.model_name = None
    self.models = []
    self.details = {}
    cancel_audio_out: bool = False
		
  def init_llm(self, host, model_name):
    self.host = host
    self.client = Client(host=f'http://{host}:{self.port}')
    self.chat_url = f'http://{host}:{self.port}/api/chat'
    self.ollama_url = self.chat_url
    # start a new conversation with the model
    self.messages = []
    dt = self.client.list()
    #self.log.info(f'Have these models: {dt}')
    self.models = dt['models']
    for mdl in self.models:
      self.log.info(f"Have: {mdl['name']}")

    self.model_name = None
    for mdl in self.models:
      if mdl['name'] == model_name:
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
    
  def list_models(self):
    return self.client.list()

  def list_model_names(self):
    mdlnm = []
    for mdl in self.models:
      mdlnm.append(mdl['name'])
    return mdlnm
    
  '''
  def call_ollama(self, messages):
    response = self.client.chat(model=self.model_name, messages=messages)
    self.log.info(f'Back from ollama: {response}')
    return True, response['message']
    
  '''
  # The streaming option using REST api (vs the ollama python api)
  # anecdotally, this seems faster. There is no logical reason for that. 
  # it appears that one (1) \n is a token. 2 are used between paragraphs
  # one to end the last line of the paragraph and one to insert a blank line
  # in the output.  
  # TODO use paragraph mark to start the tts for that paragraph and enqueue
  #   the follow on paragraphs for tts. It would be fun getting this to work.
  #
  def call_ollama(self, messages):
    r = requests.post(
        self.chat_url,
        json={"model": self.model_name, "messages": messages, "stream": True},
    )
    r.raise_for_status()
    output = ""

    for line in r.iter_lines():
        body = json.loads(line)
        if "error" in body:
            raise Exception(body["error"])
        if body.get("done") is False:
            message = body.get("message", "")
            content = message.get("content", "")
            output += content
            # the response streams one token at a time, print that as we receive it
            # TODO - advance the GUI indicator that something is happening
            if len(content) <= 1 and content=='\n': 
              print('-', end="", flush=True)
            else:
              print('+', end="", flush=True)

        if body.get("done", False):
            message["content"] = output
            return True, message
  #'''
