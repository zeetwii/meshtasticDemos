from pubsub import pub # Needed for pubsub functionality
import meshtastic # Needed for meshtastic functionality
#import meshtastic.serial_interface # Needed for serial interface
from meshtastic.ble_interface import BLEInterface # Needed for bluetooth interface

import time # Needed for time.sleep
from datetime import datetime # Needed for datetime formatting

import sys # Needed for system exit


# TODO: change this to match the other log paths
LOG_FILE = "meshtastic_node_log.txt"

def get_node_summary(interface):
    nodes = interface.nodes
    timestamp = datetime.now().isoformat()
    node_count = len(nodes)

    node_names = []
    for node_id, node_info in nodes.items():
        try:
            name = node_info['user']['longName']
        except KeyError:
            name = node_id  # Fallback to node ID
        node_names.append(name)

    summary_line = f"{timestamp} | Nodes: {node_count} | {', '.join(node_names)}"

    # Print to console
    print(summary_line)

    # Append to log file
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(summary_line + "\n")

def onReceive(packet, interface):
    """Callback function for receiving packets."""

    print(f"User ID: {packet['from']} \nMessage: {packet['decoded']['text']}")

    interface.sendText(text=f'Echo: {packet['decoded']['text']}', destinationId=packet['from'])


def onConnection(interface, topic=pub.AUTO_TOPIC):
    """Callback function for connection established."""
    print("Meshtastic interface connected.")
    # Optionally send a message on connection
    # interface.sendText("Hello from Echo Node!")

# Subscribe to receive and connection events
pub.subscribe(onReceive, "meshtastic.receive.text")
pub.subscribe(onConnection, "meshtastic.connection.established")

def main():

    #interface = meshtastic.serial_interface.SerialInterface()
    interface = BLEInterface("E2:B1:D0:23:19:06")  # Use BLEInterface for Bluetooth connection

    while True:
        get_node_summary(interface)
        time.sleep(30)



if __name__ == "__main__":
    main()
