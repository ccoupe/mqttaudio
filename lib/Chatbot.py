# Class for ollama chatbot connections and context
import requests

class Chatbot:
	def __init__(self, applog):
		self.messages = []
		self.applog = applog
		
	def init_llm(self, url, model_name):
		# pull a model 
		r = requests.post( url, json={"model": model_name})
		r.raise_for_status()
	
