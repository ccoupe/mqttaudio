import socket
import asyncio
import websockets
import time

class Test():
  def __init__(self):
    IPAddr = socket.gethostbyname(socket.gethostname()) 
    self.tb_uri = f'ws://{IPAddr}:5125/'
    print(f"wss uri: {self.tb_uri}")

  async def send_reply(self, uri, msg):
    print('mqtt:', msg) 
    # websockets 
    async with websockets.connect(uri) as ws:
      await ws.send(msg)

      
  def send1(self, name):
    asyncio.get_event_loop().run_until_complete(self.send_reply(self.tb_uri, 'name='+name))
    

if __name__ == '__main__':
  cls = Test()
  cls.send1('larry')
  time.sleep(1.5)
  cls.send1('linda')
