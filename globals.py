# Globals
# Be aware that this is done half assedly.
import enum 
from enum import IntEnum

settings = None
hmqtt = None
applog = None
muted = False
chatbot = None
cancel_audio_out: bool = False
microphone = None
recognizer = None

# Now it's getting ugly: mirroring functions
run_machine = None
