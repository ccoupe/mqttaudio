# Constants
import enum 
from enum import IntEnum

class State(enum.Enum): 
  idle = 0        # Red
  listening = 1   # Green
  chatting = 2    # Yellow
  speaking = 3    # Orange
  
class Event(enum.Enum):
  beginLoop = 0
  stop = 2
  reply = 3
  sttDone = 4
  end_speaking = 5
  switchModel = 6
