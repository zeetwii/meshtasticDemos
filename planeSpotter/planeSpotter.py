import time # needed for sleep
import os # needed for file paths
import yaml # needed for config file parsing
import threading
from meshtastic.serial_interface import SerialInterface # needed for physical connection to meshtastic
from meshtastic.util import findPorts # helper to find ports
import meshtastic # needed for random meshtastic stuff
from pubsub import pub # needed for meshtastic connection
import requests # needed for ADS-B data fetching

import ollama # needed for ollama models
import textwrap # needed for formatting text

class PlaneSpotter:

    # Tool the LLM can call to pull a filtered slice of the currently tracked aircraft,
    # instead of every aircraft being dumped into context up front.
    PLANE_SEARCH_TOOL = {
        'type': 'function',
        'function': {
            'name': 'search_aircraft',
            'description': (
                'Search the aircraft currently tracked by this sensor via ADS-B, optionally '
                'filtering by callsign, hex ID, altitude range, or minimum ground speed. Call '
                'this to look up details about specific aircraft instead of guessing.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'callsign': {
                        'type': 'string',
                        'description': 'Only return aircraft whose flight callsign contains this text, case-insensitive.',
                    },
                    'hex_id': {
                        'type': 'string',
                        'description': 'Only return aircraft whose ICAO hex ID contains this text, case-insensitive.',
                    },
                    'min_altitude': {
                        'type': 'integer',
                        'description': 'Only return aircraft at or above this altitude in feet.',
                    },
                    'max_altitude': {
                        'type': 'integer',
                        'description': 'Only return aircraft at or below this altitude in feet.',
                    },
                    'min_speed': {
                        'type': 'integer',
                        'description': 'Only return aircraft moving at or above this ground speed in knots.',
                    },
                },
                'required': [],
            },
        },
    }

    def __init__(self):
        """
        Basic init function
        """

        # Load config
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        self.model = config.get('model', 'gemma3:latest')
        self.channels = config.get('channels', [])
        self.contacts = config.get('contacts', [])
        self.device_id = config.get('device', {}).get('id')
        self.keep_alive = -1 if config.get('disable_model_timeout', False) else None
        self.checkin_interval = config.get('checkin_interval_hours') or 0

        # URL for ADS-B data (assume readsb is running locally)
        self.adsbPath = "http://localhost/tar1090/data/aircraft.json"
        #self.maxAircraft = 5  # maximum number of aircraft to report at once
        self.aircraftTimeout = 300  # seconds before an aircraft is considered "gone"

        # Track unique aircraft seen over the check-in window: hex -> last_seen epoch
        self.seen_aircraft = {}
        self.seen_lock = threading.Lock()
        self.poll_interval = 30  # seconds between background polls of aircraft.json

        # Subscribe before creating the interface — the connection.established event fires
        # during SerialInterface.__init__() from a background thread, so subscribing after
        # the constructor would always miss it.
        self.interface = None
        pub.subscribe(self.onReceive, "meshtastic.receive.text")
        pub.subscribe(self.onConnection, "meshtastic.connection.established")

        # set up meshtastic connection
        print("Initializing Plane Spotter Node...")
        ports = findPorts(eliminate_duplicates=True)  # returns ['/dev/ttyUSB0', '/dev/ttyUSB2', …]

        if len(ports) == 0:
            print("No Meshtastic devices found. Please check your connections.")
            exit(1)
        elif len(ports) == 1:
            self.interface = SerialInterface(ports[0])
            print("Connected to Meshtastic node on port:", ports[0])
            print(f"Node ID: {self.interface.getMyNodeInfo()['user']['id']}")
        else:
            print(f"Multiple Meshtastic devices found. Looking for configured device {self.device_id}...")
            self.interface = None
            for port in ports:
                try:
                    iface = SerialInterface(port)
                    node_id = iface.getMyNodeInfo()['user']['id']
                    if node_id == self.device_id:
                        self.interface = iface
                        print(f"Connected to {self.device_id} on port {port}")
                        break
                    iface.close()
                except Exception as e:
                    print(f"Could not check port {port}: {e}")
            if self.interface is None:
                print(f"Device {self.device_id} not found among available ports. Please check your config.")
                exit(1)

        # preload the ollama model
        print(f"Preloading Ollama model ({self.model})...")
        response = ollama.chat(model=self.model, keep_alive=self.keep_alive, messages=[{'role': 'system', 'content': 'Say boot up successful'}])
        print(response.message.content)

    def onConnection(self, interface):
        """
        Callback function for connection established.
        """
        # In multi-port mode we probe each port, which fires this callback for every
        # device found. Skip anything that isn't the configured target.
        node_id = interface.getMyNodeInfo()['user']['id']
        if self.device_id and node_id != self.device_id:
            return

        self.interface = interface
        print("Meshtastic connection established.")
        startup_msg = "Plane Spotter node online and connected."

        for channel in self.channels:
            idx = channel.get('index', 0)
            print(f"Sending startup message to channel {channel.get('name', idx)} (index {idx})")
            interface.sendText(startup_msg, channelIndex=idx)
            time.sleep(1)

        for contact in self.contacts:
            dest = contact.get('id')
            print(f"Sending startup message to contact {contact.get('alias', dest)}")
            interface.sendText(startup_msg, destinationId=dest)
            time.sleep(1)

        if self.checkin_interval:
            threading.Thread(target=self.pollAircraftLoop, daemon=True).start()
            threading.Thread(target=self.checkinLoop, daemon=True).start()
            print(f"Check-in thread started (every {self.checkin_interval}h)")
            print(f"Aircraft poller started (every {self.poll_interval}s)")

    def pollAircraftLoop(self):
        """
        Background thread that polls readsb's aircraft.json and records the last time
        each unique hex was observed. Entries older than the check-in window are pruned.
        """
        window_seconds = self.checkin_interval * 3600
        while True:
            aircraftList = self.fetchADSBData()
            now = time.time()
            with self.seen_lock:
                for aircraft in aircraftList:
                    hexID = aircraft.get('hex')
                    if not hexID:
                        continue
                    # only count aircraft readsb has heard from recently
                    if aircraft.get('seen', 0) > self.aircraftTimeout:
                        continue
                    self.seen_aircraft[hexID.lower()] = now
                # prune anything outside the check-in window
                cutoff = now - window_seconds
                self.seen_aircraft = {h: t for h, t in self.seen_aircraft.items() if t >= cutoff}
            time.sleep(self.poll_interval)

    def checkinLoop(self):
        """
        Background thread that sends a periodic status message to all channels and contacts.
        """
        interval_seconds = self.checkin_interval * 3600
        while True:
            time.sleep(interval_seconds)
            now = time.time()
            cutoff = now - interval_seconds
            with self.seen_lock:
                unique_count = sum(1 for t in self.seen_aircraft.values() if t >= cutoff)
            msg = (f"Plane Spotter check-in: {unique_count} unique aircraft seen "
                   f"in the last {self.checkin_interval}h.")
            print("Sending scheduled check-in message...")
            for channel in self.channels:
                idx = channel.get('index', 0)
                self.interface.sendText(msg, channelIndex=idx)
                time.sleep(1)
            for contact in self.contacts:
                dest = contact.get('id')
                self.interface.sendText(msg, destinationId=dest)
                time.sleep(1)

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

        # Fetch ADS-B data. We don't dump every aircraft into the prompt -- the model can call
        # search_aircraft to pull a filtered slice as needed.
        aircraftList = self.fetchADSBData()
        total = sum(1 for a in aircraftList if a.get('seen', 0) <= self.aircraftTimeout)

        messages = [
            {'role': 'system', 'content': (
                'You are an automated sensor node that provides real-time information about nearby '
                'aircraft based on ADS-B data. You communicate with users over a Meshtastic network '
                'and respond to their queries in a concise and informative manner. '
                f'There are currently {total} aircraft being tracked nearby. Use the search_aircraft '
                'tool to look up details (filtering by callsign, hex ID, altitude range, or minimum '
                'ground speed) before answering -- do not guess at details you have not looked up. '
                "If no aircraft are nearby or match the user's request, say so."
            )},
            {'role': 'user', 'content': packet['decoded']['text']}
        ]

        response = None
        for _ in range(3):  # cap tool-call rounds in case the model gets stuck calling tools
            response = ollama.chat(model=self.model, keep_alive=self.keep_alive, messages=messages, tools=[self.PLANE_SEARCH_TOOL])
            messages.append(response.message)

            if not response.message.tool_calls:
                break

            for call in response.message.tool_calls:
                args = {k: v for k, v in (call.function.arguments or {}).items()
                        if k in ('callsign', 'hex_id', 'min_altitude', 'max_altitude', 'min_speed')}
                results = self.summarizeAircraft(aircraftList, **args)
                messages.append({'role': 'tool', 'tool_name': call.function.name, 'content': '\n'.join(results)})

        replyText = response.message.content or "Sorry, I couldn't come up with a response to that."
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
        
    def summarizeAircraft(self, aircraftList, callsign=None, hex_id=None, min_altitude=None, max_altitude=None, min_speed=None):
        """
        Creates a madlib string summary of each aircraft matching the given filters, both for
        debugging and to pass into the LLM as context. All filters are optional and combine
        with AND; call with no filters to summarize every currently-tracked aircraft.

        Args:
            aircraftList (list): the list of aircraft data dictionaries
            callsign (str, optional): only include aircraft whose callsign contains this text (case-insensitive)
            hex_id (str, optional): only include aircraft whose hex ID contains this text (case-insensitive)
            min_altitude (int, optional): only include aircraft at or above this altitude (feet)
            max_altitude (int, optional): only include aircraft at or below this altitude (feet)
            min_speed (int, optional): only include aircraft at or above this ground speed (knots)

        Returns:
            list: human readable summary strings, ending with a match count.
        """

        def toFloat(value):
            try:
                return float(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        min_altitude = toFloat(min_altitude)
        max_altitude = toFloat(max_altitude)
        min_speed = toFloat(min_speed)

        summaries = []
        total = 0

        for aircraft in aircraftList:

            seen = aircraft.get('seen', 0)
            if seen > self.aircraftTimeout:
                continue  # skip aircraft that haven't been seen recently

            total += 1  # count valid aircraft

            flightCallsign = (aircraft.get('flight') or aircraft.get('tisb') or "Unknown").strip()
            hexID = aircraft.get('hex', 'N/A').upper()

            altitude = aircraft.get("alt_baro")
            if altitude is None:
                altitude = aircraft.get("alt_geom")

            speed = aircraft.get('gs')  # ground speed
            lat = aircraft.get('lat')
            lon = aircraft.get('lon')

            if callsign and callsign.lower() not in flightCallsign.lower():
                continue
            if hex_id and hex_id.lower() not in hexID.lower():
                continue
            if min_altitude is not None and not (isinstance(altitude, (int, float)) and altitude >= min_altitude):
                continue
            if max_altitude is not None and not (isinstance(altitude, (int, float)) and altitude <= max_altitude):
                continue
            if min_speed is not None and not (isinstance(speed, (int, float)) and speed >= min_speed):
                continue

            summary = f"Flight {flightCallsign} (Hex ID: {hexID}) is at an altitude of {altitude} feet, moving at {speed} knots, located at coordinates ({lat}, {lon})."
            print(summary)
            summaries.append(summary)

        summaries.append(f"{len(summaries)} of {total} total aircraft match this filter.")

        return summaries


if __name__ == "__main__":
    planeSpotter = PlaneSpotter()

    try:
        while True:
            time.sleep(10)  # keep the main thread alive
    except KeyboardInterrupt:
        print("Exiting Plane Spotter Node...")