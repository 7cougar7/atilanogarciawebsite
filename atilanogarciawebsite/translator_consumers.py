import base64
import json
import threading
from channels.generic.websocket import WebsocketConsumer
from google.cloud import speech
from atilanogarciawebsite.speech_client_bridge import SpeechClientBridge


def on_transcription_response(response):
    if not response.results:
        return

    result = response.results[0]
    if not result.alternatives:
        return

    transcription = result.alternatives[0].transcript
    print(transcription)


class CallConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.MULAW,
            sample_rate_hertz=8000,
            language_code="en-US",
        )
        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.config, interim_results=True
        )

    def connect(self):
        self.accept()
        self.bridge = SpeechClientBridge(
            self.streaming_config, on_transcription_response
        )
        t = threading.Thread(target=self.bridge.start)
        t.start()
        print("New Connection Initiated")

    def disconnect(self, close_code):
        self.bridge.terminate()

    def receive(self, text_data):
        message = json.loads(text_data)
        event = message["event"]
        if event == "connected":
            print(f"{message=}")
            print("A new call has connected")

        elif event == "start":
            print(f'{message["start"]["customParameters"]["phoneNumber"]=}')

        elif event == "media":
            media = message["media"]
            chunk = base64.b64decode(media["payload"])
            self.bridge.add_request(chunk)

        elif event == "stop":
            print("Call has Ended")
