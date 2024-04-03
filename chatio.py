# Module for speechio functions
#
import globals

# much of the Glados stuff is borrowed from nerdaxic: 
# Note 'aplay' is synchronous - we wait in playFile until
# the sound is finished playing or cancelled
# Was  call(["aplay", "-q", filename])	
#

def playFile(filename):
  global cancel_audio_out, applog
  chunk: int = 1024
  applog.info(f"Playing {filename}")
  # There is a race condition possible with cancel_audio_out
  # I think.
  cancel_audio_out = False
  with wave.open(filename, 'rb') as wf:
    
      def callback(in_data, frame_count, time_info, status):
        if cancel_audio_out:
          cancel_audio_out = False
          data = [] # a len of 0 means we are at the end
        else:
          data = wf.readframes(frame_count)
        # If len(data) is less than requested frame_count, PyAudio automatically
        # assumes the stream is finished, and the stream stops.
        return (data, pyaudio.paContinue)

      # Instantiate PyAudio and initialize PortAudio system resources (1)
      p = pyaudio.PyAudio()
  
      # Open stream (2)
      stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                      channels=wf.getnchannels(),
                      rate=wf.getframerate(),
                      output=True,
                      stream_callback=callback)
  
      # Wait for stream to finish (4)
      while stream.is_active():
          time.sleep(0.1)
      
      # Close the stream (5)
      stream.close()
      
      # Release PortAudio system resources (6)
      p.terminate()

