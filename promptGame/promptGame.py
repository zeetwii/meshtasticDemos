
from meshtastic.serial_interface import SerialInterface # needed for physical connection to meshtastic
from meshtastic.util import findPorts # helper to find ports
from pubsub import pub # needed for meshtastic connection

import datetime # needed for logging
import os # needed for logging
import json # needed for logging

from ollama import chat # needed for ollama message generation
from ollama import ChatResponse # needed for ollama message generation

import time # needed for sleep

class PromptGame:

    def __init__(self):

        # set up logging folders
        os.makedirs("./logs", exist_ok=True)
        os.makedirs("./logs/players", exist_ok=True)
        os.makedirs("./logs/nodes", exist_ok=True)

        ports = findPorts(eliminate_duplicates=True)  # returns ['/dev/ttyUSB0', '/dev/ttyUSB2', …]

        if len(ports) == 1:  # if only one port found, assume it's the defcon radio
            self.interface = SerialInterface(ports[0])  # connect to the first port
            print("Connected to Meshtastic node on port:", ports[0])
        else:
            print("Multiple or no Meshtastic devices found. Please check your connections.")
            exit(1)

        # Subscribe to receive and connection events
        pub.subscribe(self.onReceive, "meshtastic.receive.text")
        pub.subscribe(self.onConnection, "meshtastic.connection.established")


    def onReceive(self, packet, interface):
        """Callback function for receiving packets."""

        print(f"User ID: {packet['from']} \nMessage: {packet['decoded']['text']}")

        # Generate a response using Ollama
        response: ChatResponse = chat(model='gemma3n:latest', messages=[
        {
            'role': 'user', 'content': f'{packet["decoded"]["text"]}',
        },
        ])


        print(response.message.content)

        # Send the response back to the sender
        interface.sendText(text=f'{response.message.content}', destinationId=packet['from'])

    def onConnection(self, interface, topic=pub.AUTO_TOPIC):
        """Callback function for connection established."""
        print("Meshtastic interface connected.")
        
        interface.sendText("Hello from the AI Village Prompt Injection Game!  Send me a direct message to start your version of the game and score points.  ")

    def logNodes(self):
        """Logs the current nodes in the network."""
        nodes = self.interface.nodes
        timestamp = datetime.datetime.now().isoformat()
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S") # formatted to be windows friendly
        node_count = len(nodes)
        node_names = []
        for node_id, node_info in nodes.items():
            try:
                name = node_info['user']['longName']
            except KeyError:
                name = node_id  # Fallback to node ID
            node_names.append(name)

        # Write log to JSON file
        log_entry = {
            'timestamp': timestamp,
            'node_count': node_count,
            'nodes': node_names
        }

        # Create a log file with timestamp
        
        log_file = f"./logs/nodes/{timestamp_str}.json"
        with open(log_file, "w") as f:
            json.dump(log_entry, f, indent=4)
        print(f"Logged nodes to {log_file}")
        



if __name__ == '__main__':
    promptGame = PromptGame()

    while True:
        # Keep the script running to listen for messages
        promptGame.logNodes()  # Log nodes every minute
        time.sleep(60)