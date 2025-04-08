# Globals Vars - gvars.py
# Feels half assed.
# from enum import IntEnum
from queue import Queue
from threading import Lock, Thread

# settings = None # NO NO NO This does not belong here
muted = False
# chatbot = None
cancel_audio_out: bool = False
microphone = None
recognizer = None
# Note run_machine is a reference to a fuction (we call it) as is applog
# hmqtt. recognizer and microphone?
run_machine = None
applog = None
hmqtt = None
settings = None
tts_queue: Queue = None
tts_thread: Thread = None
play_queue: Queue = None
play_thread: Thread = None
play_lock: Lock = None
