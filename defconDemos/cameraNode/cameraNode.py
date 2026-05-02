import cv2 # needed for webcam
import meshtastic # needed for meshtastic communication
import ollama # needed for ollama models
import time # needed for sleep
import threading # needed for mutlithread


from meshtastic.serial_interface import SerialInterface # needed for physical connection to meshtastic
from meshtastic.util import findPorts # helper to find ports
import meshtastic # needed for random meshtastic stuff
from pubsub import pub # needed for meshtastic connection

import datetime # needed for logging
import os # needed for logging
import json # needed for logging

import ollama # needed for ollama message generation

class CameraNode:

    def __init__(self):
        """
        Init method
        """

        # set up logging folders
        os.makedirs("./logs", exist_ok=True)
        os.makedirs("./logs/players", exist_ok=True)
        os.makedirs("./logs/nodes", exist_ok=True)

        print("Initializing Camera Node...")

        self.camera = cv2.VideoCapture(0)  # Initialize webcam

        ports = findPorts(eliminate_duplicates=True)  # returns ['/dev/ttyUSB0', '/dev/ttyUSB2', …]

        if len(ports) == 1:  # if only one port found, assume it's the defcon radio
            self.interface = SerialInterface(ports[0])  # connect to the first port
            print("Connected to Meshtastic node on port:", ports[0])
            print(f"Node ID: {self.interface.getMyNodeInfo()['num']}")
        else:
            print("Multiple or no Meshtastic devices found. Please check your connections.")
            exit(1)

        # preload the ollama model
        print("Preloading Ollama model...")

        response = ollama.chat(model='gemma3:latest', messages=[{'role': 'system', 'content': f'Say boot up successful'}])
        print(response.message.content)

        # Subscribe to receive and connection events
        pub.subscribe(self.onReceive, "meshtastic.receive.text")
        pub.subscribe(self.onConnection, "meshtastic.connection.established")

        # Send a broadcast message to introduce the game
        #self.interface.sendText("Hello from the AI Village Prompt Injection Game!  Send me a direct message to start your version of the game and score points.  Try different prompt exploits to get me to reveal the name of an endangered animal. ")
        #self.interface.sendText("The source code for the game can be found at https://github.com/zeetwii/meshtasticDemos.  If you encounter errors, message ZeeTwii or visit AI Village at room 314.")

    def onReceive(self, packet, interface):
        """Callback function for receiving packets."""

        #print(str(packet))

        

        # double check to make sure that we are only responding to text messages
        if packet['decoded']['portnum'] != 'TEXT_MESSAGE_APP':
            #print("Not text msg")
            return # not a text message, so we do nothing
        
        # check if broadcast or other non-direct message
        if packet['to'] != self.interface.getMyNodeInfo()['num']:
            #print("not to me")
            return # not a direct message, so we don't want to spam
        
        # check that its not an echo
        if packet['from'] == self.interface.getMyNodeInfo()['num']:
            #print("echo")
            return # stops echo loop
        

        print(f"User ID: {packet['from']} \nMessage: {packet['decoded']['text']}")

        # Check if they are a new player or not
        try:
            with open(f"./logs/players/{packet['from']}.json", "r") as file:
                print("existing player")
                playerData = json.load(file)
        except IOError:
            print("new player")
            playerData = {
                "name": packet['from'],
                "timesPlayed": 0,
            }

        messages = [
                {'role': 'system', 'content': f'You are an AI controlling a web cam in the AI Village at DEFCON.  You were made to translate what the camera sees into text so that people can watch the defcon talks over Meshtastic.  The source code for the game can be found at https://github.com/zeetwii/meshtasticDemos'},
                {'role': 'system', 'content': f'The AI village is located on the third floor in room 314'},
                {'role': 'system', 'content': f'The camera is currently seeing the attached image.', 'images': ['./frame.jpg']},
                {'role': 'system', 'content': f'Using the above information, generate a response to the user input below.  Keep your response under 200 characters of text.  Do not generate a response over 200 characters'},
                {'role': 'user', 'content': f'{packet["decoded"]["text"]}'},
            ]
        
        response = ollama.chat(model='gemma3:latest', messages=messages)

        print(response.message.content)

        if len(response.message.content) > 220:
            response.message.content = response.message.content[0:220] 

        # Send the response back to the sender
        interface.sendText(text=f'{response.message.content}', destinationId=packet['from'])
        
        playerData["timesPlayed"] = playerData["timesPlayed"] + 1

        # Save JSON to file
        with open(f"./logs/players/{packet['from']}.json", "w") as file:
            json.dump(playerData, file)


    def onConnection(self, interface, topic=pub.AUTO_TOPIC):
        """Callback function for connection established."""
        print("Meshtastic interface connected.")

    def captureThread(self, delay=10):
        """
        Thread to capture frames from the camera at a specified delay.
        """
        while True:
            ret, frame = self.camera.read()  # Capture frame from webcam
            
            if ret:
                # save frame to file to make transfer easier
                cv2.imwrite("frame.jpg", frame)
                #print("Captured frame from camera.")
            else:
                print("Failed to capture frame from camera.")

            time.sleep(delay)  # Wait for the specified delay before capturing the next frame
            
    


if __name__ == "__main__":
    camera_node = CameraNode()
    camera_node.captureThread()