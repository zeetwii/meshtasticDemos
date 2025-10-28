import time # needed for sleep
from meshtastic.serial_interface import SerialInterface # needed for physical connection to meshtastic
from meshtastic.util import findPorts # helper to find ports
import meshtastic # needed for random meshtastic stuff
from pubsub import pub # needed for meshtastic connection
import requests # needed for ADS-B data fetching

import ollama # needed for ollama models
import textwrap # needed for formatting text

class PlaneSpotter:

    def __init__(self):
        """
        Basic init function
        """

        # URL for ADS-B data (assume readsb is running locally)
        self.adsbPath = "http://localhost/tar1090/data/aircraft.json"
        #self.maxAircraft = 5  # maximum number of aircraft to report at once 
        self.aircraftTimeout = 300  # seconds before an aircraft is considered "gone"

         # set up meshtastic connection
        print("Initializing Plane Spotter Node...")
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

    def onConnection(self, interface):
        """
        Callback function for connection established.
        """
        print("Meshtastic connection established.")

    def onReceive(self, packet, interface):
        """
        Callback function for receiving packets.
        """
        
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

        # Fetch ADS-B data
        aircraftList = self.fetchADSBData()
        summaries = self.summarizeAircraft(aircraftList)

        # Create response message
        messages = [
            {'role': 'system', 'content': 'You are an automated sensor node that provides real-time information about nearby aircraft based on ADS-B data. You communicate with users over a Meshtastic network and respond to their queries in a concise and informative manner.'},
            {'role': 'system', 'content': f'Here is the current data from the ADS-B sensor: {str(summaries)}'},
            {'role': 'system', 'content': 'Using the provided ADS-B data, respond to the user\'s query in a concise manner. If no aircraft are nearby, inform the user accordingly.'},
            {'role': 'user', 'content': packet['decoded']['text']}
        ]

        response = ollama.chat(model='gemma3:latest', messages=messages)
        replyText = response.message.content
        print(f"Replying with: {replyText}")

        # break reply into chunks if too long
        replyLines = textwrap.wrap(replyText, width=220) # Meshtastic has a limit of 230 characters per message

        # Send response back to user
        #self.interface.sendText(replyText, destinationId=packet['from'])
        for line in replyLines:
            self.interface.sendText(line, destinationId=packet['from'])
            time.sleep(1)  # brief pause between messages to avoid flooding

    def fetchADSBData(self):
        """
        Fetch ADS-B data from the local dump1090/readsb instance.
        """

        try:
            response = requests.get(self.adsbPath, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get('aircraft', [])
        except Exception as e:
            print("Error fetching ADS-B data:", e)
            return []
        
    def summarizeAircraft(self, aircraftList):
        """
        Creates a madlib string summery of each aircraft for both debugging and to pass into llm

        Args:
            aircraftList (list): the list of aircraft data dictionaries
        """

        summaries = []
        count = 0

        for aircraft in aircraftList:
            
            seen = aircraft.get('seen', 0)
            if seen > self.aircraftTimeout:
                continue  # skip aircraft that haven't been seen recently

            count += 1 # count valid aircraft

            callsign = (aircraft.get('flight') or aircraft.get('tisb') or "N/A").strip()
            hexID = aircraft.get('hex', 'N/A').upper()

            altitude = aircraft.get("alt_baro")
            if altitude is None:
                altitude = aircraft.get("alt_geom")

            speed = aircraft.get('gs')  # ground speed
            lat = aircraft.get('lat')
            lon = aircraft.get('lon')
            summary = f"Flight {callsign} (Hex ID: {hexID}) is at an altitude of {altitude} feet, moving at {speed} knots, located at coordinates ({lat}, {lon})."
            print(summary)
            summaries.append(summary)

        summaries.append(f"Total aircraft currently monitoring: {count}")

        return summaries


if __name__ == "__main__":
    planeSpotter = PlaneSpotter()

    try:
        while True:
            time.sleep(10)  # keep the main thread alive
    except KeyboardInterrupt:
        print("Exiting Plane Spotter Node...")