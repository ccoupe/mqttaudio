# import pyaudio
import speech_recognition as sr

m = None
print('Pyaudio and SpeechRecog devices:')
mic = sr.Microphone()
for i, microphone_name in enumerate(mic.list_microphone_names()):
  if microphone_name == 'pulse':
    print(i, microphone_name)
  else:
    print(microphone_name)
