import time # needed for sleep
import os # needed for file paths and system commands
import sys # needed for platform checks and exit
import csv # needed for manufacturer lookup
import yaml # needed for config file parsing
import threading
import subprocess # needed for channel enumeration

from scapy.all import sniff, Dot11, Dot11Beacon, Dot11Elt # needed for reading wifi beacons

from meshtastic.serial_interface import SerialInterface # needed for physical connection to meshtastic
from meshtastic.util import findPorts # helper to find ports
import meshtastic # needed for random meshtastic stuff
from pubsub import pub # needed for meshtastic connection

import ollama # needed for ollama models
import textwrap # needed for formatting text


class WifiNetwork:
    """
    Represents a single wifi access point seen by the scanner, along with the
    last time its beacon was observed so stale networks can be aged out.
    """

    def __init__(self, bssid, ssid, dBm, channel, crypto, vendor="Unknown"):
        self.bssid = bssid
        self.ssid = ssid
        self.dBm = dBm
        self.channel = channel
        self.crypto = crypto
        self.vendor = vendor
        self.last_seen = time.time()

    def update(self, ssid, dBm, channel, crypto):
        """Refresh this network's details and last-seen timestamp from a new beacon."""
        self.ssid = ssid
        self.dBm = dBm
        self.channel = channel
        self.crypto = crypto
        self.last_seen = time.time()


class WifiSpotter:

    # Tool the LLM can call to pull a filtered slice of the currently detected networks,
    # instead of every network being dumped into context up front.
    WIFI_SEARCH_TOOL = {
        'type': 'function',
        'function': {
            'name': 'search_wifi_networks',
            'description': (
                'Search the WiFi networks currently detected by this sensor, optionally '
                'filtering by channel, SSID, security type, vendor, or minimum signal '
                'strength. Call this to look up details about specific networks instead '
                'of guessing.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'channel': {
                        'type': 'integer',
                        'description': 'Only return networks broadcasting on this WiFi channel number.',
                    },
                    'ssid': {
                        'type': 'string',
                        'description': 'Only return networks whose name (SSID) contains this text, case-insensitive.',
                    },
                    'security': {
                        'type': 'string',
                        'description': 'Only return networks whose security info contains this text, e.g. "WPA2".',
                    },
                    'vendor': {
                        'type': 'string',
                        'description': 'Only return networks whose hardware vendor contains this text.',
                    },
                    'min_dbm': {
                        'type': 'integer',
                        'description': 'Only return networks with signal strength at or above this dBm value (closer to 0 is stronger).',
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
        self.wifi_interface = config.get('wifi_interface')

        # how long since a beacon was last heard before a network is considered "gone"
        self.networkTimeout = 300  # seconds

        # Track unique networks seen: bssid -> WifiNetwork
        self.seen_networks = {}
        self.seen_lock = threading.Lock()

        # Load the IEEE OUI -> vendor lookup tables
        self.vendorDict = {}
        self.loadVendorDict()

        # Subscribe before creating the interface — the connection.established event fires
        # during SerialInterface.__init__() from a background thread, so subscribing after
        # the constructor would always miss it.
        self.interface = None
        pub.subscribe(self.onReceive, "meshtastic.receive.text")
        pub.subscribe(self.onConnection, "meshtastic.connection.established")

        # set up meshtastic connection
        print("Initializing WiFi Spotter Node...")
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

    def loadVendorDict(self):
        """
        Builds the OUI -> vendor lookup from the three IEEE registry CSVs. Files are read
        relative to this script so it works regardless of the current working directory.
        Missing files are skipped so the node still runs (vendors just show as Unknown).
        """

        base = os.path.dirname(os.path.abspath(__file__))
        for filename in ('oui.csv', 'mam.csv', 'oui36.csv'):
            path = os.path.join(base, filename)
            try:
                with open(path, mode='r', encoding='utf-8', errors='replace') as infile:
                    reader = csv.reader(infile)
                    self.vendorDict.update({rows[1]: rows[2] for rows in reader if len(rows) >= 3})
            except FileNotFoundError:
                print(f"Vendor registry {filename} not found — run macUpdater.py to download it.")
        print(f"Loaded {len(self.vendorDict)} vendor OUI entries.")

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
        startup_msg = "WiFi Spotter node online and connected."

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

        # Put the interface into monitor mode before starting the sniffer thread.
        # Doing this concurrently (e.g. inside channelHopper) races scapy's sniff(),
        # which can open its socket while ifconfig has briefly taken the interface
        # down, failing with "Network is down" and exiting without retrying.
        self.setupInterface()

        # Always start sniffing so query responses have live data, even if check-ins are off.
        threading.Thread(target=self.startSniffer, daemon=True).start()
        threading.Thread(target=self.channelHopper, daemon=True).start()
        print(f"WiFi sniffer started on interface {self.wifi_interface}")

        if self.checkin_interval:
            threading.Thread(target=self.checkinLoop, daemon=True).start()
            print(f"Check-in thread started (every {self.checkin_interval}h)")

    def setupInterface(self):
        """
        Puts the interface into monitor mode (Linux only). Returns True on success.
        """

        if not self.wifi_interface:
            print("No wifi_interface configured. Skipping monitor mode setup.")
            return False

        if not sys.platform.startswith('linux'):
            print(f"Monitor mode setup skipped on {sys.platform}; relying on the adapter being in monitor mode already.")
            return True

        print(f"Placing {self.wifi_interface} into monitor mode")
        os.system('ifconfig ' + self.wifi_interface + ' down')
        try:
            os.system('iwconfig ' + self.wifi_interface + ' mode monitor')
        except Exception:
            print("Failed to setup monitor mode")
            return False
        os.system('ifconfig ' + self.wifi_interface + ' up')
        return True

    def getValidChannels(self):
        """
        Generates the list of valid channels for the interface using iwlist (Linux). Falls
        back to the standard 2.4GHz channels if iwlist is unavailable.

        Returns:
            list: channel numbers (as strings) to hop through.
        """

        validChannel = {'01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14'}
        try:
            channelText = subprocess.run(['iwlist', str(self.wifi_interface), 'freq'], capture_output=True, text=True).stdout
            for line in channelText.splitlines():
                if "Channel" in line and "Current" not in line:
                    validChannel.add(line.split()[1])
        except FileNotFoundError:
            pass  # iwlist not present (e.g. non-Linux) — stick with the 2.4GHz defaults
        return sorted(validChannel)

    def channelHopper(self):
        """
        Background thread that sweeps the interface across all valid channels so beacons on
        every channel get a chance to be heard. No-op on platforms without iwconfig.
        """

        if not sys.platform.startswith('linux'):
            return  # channel hopping needs iwconfig; the adapter handles its own channel otherwise

        validChannel = self.getValidChannels()
        while True:
            for channel in validChannel:
                os.system(f"iwconfig {self.wifi_interface} channel {channel}")
                time.sleep(0.2)  # dwell time per channel

    def startSniffer(self):
        """
        Runs scapy's blocking beacon sniffer. Restarts itself if scapy throws, so a transient
        error doesn't permanently kill data collection.
        """

        try:
            sniff(prn=self.beaconCallback, iface=self.wifi_interface, store=False)
        except Exception as e:
            print(f"Sniffer error ({e}); restarting in 5s...")
            time.sleep(5)
            self.startSniffer()

    def beaconCallback(self, packet):
        """
        Parses a captured beacon frame and records/updates the network in seen_networks.
        """

        if not packet.haslayer(Dot11Beacon):
            return  # only interested in access point beacons

        bssid = packet[Dot11].addr2
        try:
            ssid = packet[Dot11Elt].info.decode(errors='replace') or "(hidden)"
        except Exception:
            ssid = "(hidden)"

        try:
            dbm_signal = packet.dBm_AntSignal
        except Exception:
            dbm_signal = "N/A"

        stats = packet[Dot11Beacon].network_stats()
        channel = stats.get("channel")
        crypto = stats.get("crypto")

        # OUI key for vendor lookup: first 6 hex chars of the MAC, no separators, uppercase
        key = str(bssid).replace(':', '').upper()[0:6]
        vendor = self.vendorDict.get(key, "Unknown")

        with self.seen_lock:
            existing = self.seen_networks.get(bssid)
            if existing:
                existing.update(ssid, dbm_signal, channel, crypto)
            else:
                self.seen_networks[bssid] = WifiNetwork(bssid, ssid, dbm_signal, channel, crypto, vendor)

    def activeNetworks(self):
        """
        Returns the list of networks heard within the timeout window, pruning anything older
        from the tracking dict so it doesn't grow unbounded.

        Returns:
            list: WifiNetwork objects currently considered active.
        """

        now = time.time()
        cutoff = now - self.networkTimeout
        with self.seen_lock:
            self.seen_networks = {b: n for b, n in self.seen_networks.items() if n.last_seen >= cutoff}
            return list(self.seen_networks.values())

    def summarizeNetworks(self, networks, channel=None, ssid=None, security=None, vendor=None, min_dbm=None):
        """
        Creates a madlib string summary of each network matching the given filters, both for
        debugging and to pass into the LLM as context. All filters are optional and combine
        with AND; call with no filters to summarize every network.

        Args:
            networks (list): the list of WifiNetwork objects to summarize
            channel (int, optional): only include networks on this channel
            ssid (str, optional): only include networks whose SSID contains this text (case-insensitive)
            security (str, optional): only include networks whose security info contains this text (case-insensitive)
            vendor (str, optional): only include networks whose vendor contains this text (case-insensitive)
            min_dbm (int, optional): only include networks with signal strength >= this value

        Returns:
            list: human readable summary strings, ending with a match count.
        """

        filtered = networks
        if channel is not None:
            filtered = [n for n in filtered if str(n.channel) == str(channel)]
        if ssid:
            filtered = [n for n in filtered if ssid.lower() in n.ssid.lower()]
        if security:
            filtered = [n for n in filtered if security.lower() in (n.crypto or '').lower()]
        if vendor:
            filtered = [n for n in filtered if vendor.lower() in (n.vendor or '').lower()]
        if min_dbm is not None:
            try:
                min_dbm = float(min_dbm)
                filtered = [n for n in filtered if isinstance(n.dBm, (int, float)) and n.dBm >= min_dbm]
            except (TypeError, ValueError):
                pass

        summaries = []
        for net in filtered:
            summary = (f"Network '{net.ssid}' (BSSID: {net.bssid}, vendor: {net.vendor}) "
                       f"is on channel {net.channel}, signal {net.dBm} dBm, security: {net.crypto}.")
            print(summary)
            summaries.append(summary)

        summaries.append(f"{len(filtered)} of {len(networks)} total networks match this filter.")
        return summaries

    def checkinLoop(self):
        """
        Background thread that sends a periodic status message to all channels and contacts.
        """

        interval_seconds = self.checkin_interval * 3600
        while True:
            time.sleep(interval_seconds)
            unique_count = len(self.activeNetworks())
            msg = (f"WiFi Spotter check-in: {unique_count} unique networks currently "
                   f"detected nearby.")
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

        # double check to make sure that we are only responding to text messages
        if packet['decoded']['portnum'] != 'TEXT_MESSAGE_APP':
            return  # not a text message, so we do nothing

        # check if broadcast or other non-direct message
        if packet['to'] != self.interface.getMyNodeInfo()['num']:
            return  # not a direct message, so we don't want to spam

        # check that its not an echo
        if packet['from'] == self.interface.getMyNodeInfo()['num']:
            return  # stops echo loop

        print(f"User ID: {packet['from']} \nMessage: {packet['decoded']['text']}")

        # Gather the currently visible wifi networks. We don't dump them all into the prompt --
        # the model can call search_wifi_networks to pull a filtered slice as needed.
        networks = self.activeNetworks()

        messages = [
            {'role': 'system', 'content': (
                'You are an automated sensor node that provides real-time information about nearby '
                'WiFi networks based on 802.11 beacon scanning. You communicate with users over a '
                'Meshtastic network and respond to their queries in a concise and informative manner. '
                f'There are currently {len(networks)} networks detected nearby. Use the '
                'search_wifi_networks tool to look up details (filtering by channel, SSID, security, '
                'vendor, or signal strength) before answering -- do not guess at details you have not '
                "looked up. If no networks are nearby or match the user's request, say so."
            )},
            {'role': 'user', 'content': packet['decoded']['text']}
        ]

        response = None
        for _ in range(3):  # cap tool-call rounds in case the model gets stuck calling tools
            response = ollama.chat(model=self.model, keep_alive=self.keep_alive, messages=messages, tools=[self.WIFI_SEARCH_TOOL])
            messages.append(response.message)

            if not response.message.tool_calls:
                break

            for call in response.message.tool_calls:
                args = {k: v for k, v in (call.function.arguments or {}).items()
                        if k in ('channel', 'ssid', 'security', 'vendor', 'min_dbm')}
                results = self.summarizeNetworks(networks, **args)
                messages.append({'role': 'tool', 'tool_name': call.function.name, 'content': '\n'.join(results)})

        replyText = response.message.content or "Sorry, I couldn't come up with a response to that."
        print(f"Replying with: {replyText}")

        # break reply into chunks if too long
        replyLines = textwrap.wrap(replyText, width=220)  # Meshtastic has a limit of 230 characters per message

        # Send response back to user
        for line in replyLines:
            self.interface.sendText(line, destinationId=packet['from'])
            time.sleep(1)  # brief pause between messages to avoid flooding


if __name__ == "__main__":
    wifiSpotter = WifiSpotter()

    try:
        while True:
            time.sleep(10)  # keep the main thread alive
    except KeyboardInterrupt:
        print("Exiting WiFi Spotter Node...")
