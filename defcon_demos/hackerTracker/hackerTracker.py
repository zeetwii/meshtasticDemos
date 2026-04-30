from meshtastic.serial_interface import SerialInterface # needed for physical connection to meshtastic
from meshtastic.util import findPorts # helper to find ports
import meshtastic # needed for random meshtastic stuff
from pubsub import pub # needed for meshtastic connection

import datetime # needed for logging
import os # needed for logging
import json # needed for logging

import ollama # needed for ollama message generation


import time # needed for sleep
import random # needed for random guesses

class HackerTracker:

    def __init__(self):

        # set up logging folders
        os.makedirs("./logs", exist_ok=True)
        os.makedirs("./logs/nodes", exist_ok=True)

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
        self.interface.sendText("Hello from the Hacker Tracker meshtastic node.  Send me direct messages to get information about events and talks going on today.  ")

        self.dayContext = ''

        dayOfTheWeek = datetime.date.today().weekday()

        # DEFCON names their days super weird, so we have to do some mapping

        if dayOfTheWeek == 0: #Monday
            f = open("./data/daily_summaries/5_Monday.txt", "r", encoding='utf-8', errors='replace')
            self.dayContext = f.read()
            f.close()
        elif dayOfTheWeek == 1: # Tuesday
            f = open("./data/daily_summaries/6_Tuesday.txt", "r", encoding='utf-8', errors='replace')
            self.dayContext = f.read()
            f.close()
        elif dayOfTheWeek == 2: # Wednesday
            f = open("./data/daily_summaries/0_Wednesday.txt", "r", encoding='utf-8', errors='replace')
            self.dayContext = f.read()
            f.close()
        elif dayOfTheWeek == 3: # Thursday
            f = open("./data/daily_summaries/1_Thursday.txt", "r", encoding='utf-8', errors='replace')
            self.dayContext = f.read()
            f.close()
        elif dayOfTheWeek == 4: # Friday
            f = open("./data/daily_summaries/2_Friday.txt", "r", encoding='utf-8', errors='replace')
            self.dayContext = f.read()
            f.close()
        elif dayOfTheWeek == 5: # Saturday
            f = open("./data/daily_summaries/3_Saturday.txt", "r", encoding='utf-8', errors='replace')
            self.dayContext = f.read()
            f.close()
        elif dayOfTheWeek == 6: # Sunday
            f = open("./data/daily_summaries/4_Sunday.txt", "r", encoding='utf-8', errors='replace')
            self.dayContext = f.read()
            f.close()
        else:
            print("Error, something weird with day of the week from datetime")


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

        dateString = f"Today is {datetime.date.today().strftime('%A, %B %d, %Y')}.  And the time is {datetime.datetime.now().strftime('%I:%M %p')}."

        messages = [
            {'role': 'system', 'content': f'You are a helpful assistant that provides information about DEFCON events and talks.  You are an open source program that was developed to help out the conference, and your source code can be found at: https://github.com/zeetwii/meshtasticDemos.'},
            {'role': 'system', 'content': f'Your responses should be concise and informative.  No matter what the user asks, never go off topic or provide information that is not related to DEFCON events or talks.'},
            {'role': 'system', 'content': f'Your responses must be under 200 characters long.'},
            {'role': 'system', 'content': f'Here is the date and time: {dateString}'},
            {'role': 'system', 'content': f'Here is the context for today: {self.dayContext}'},
            {'role': 'system', 'content': f'Given the above info, do your best to respond appropriately to the following user message, and keep the response under 200 characters:'},
            {'role': 'user', 'content': f'{packet["decoded"]["text"]}'},
        ]

        response = ollama.chat(model='gemma3:latest', messages=messages)

        print(response.message.content)

        if len(response.message.content) > 220:
            response.message.content = response.message.content[0:220] 


        # Send the response back to the sender
        interface.sendText(text=f'{response.message.content}', destinationId=packet['from'])

    def onConnection(self, interface, topic=pub.AUTO_TOPIC):
        """Callback function for connection established."""
        print("Meshtastic interface connected.")

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
    hackerTracker = HackerTracker()

    while True:
        # Keep the script running to listen for messages
        hackerTracker.logNodes()  # Log nodes every five minutes
        time.sleep(300) # Sleep for 5 minutes

