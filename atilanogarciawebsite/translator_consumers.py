import json
from channels.generic.websocket import WebsocketConsumer


class CallConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        print("New Connection Initiated")

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        message = json.loads(text_data)
        event = message["event"]
        if event == "connected":
            print("A new call has connected")
        elif event == "started":
            print(f"Starting Media Stream {message.streamSid}")
        elif event == "media":
            print("Receiving Audio...")
        elif event == "stop":
            print("Call has Ended")
