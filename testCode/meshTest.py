import meshtastic
from meshtastic.serial_interface import SerialInterface
from meshtastic.protobuf.config_pb2 import Config       # brings in the enum helper
from meshtastic.util import findPorts          # helper


ports = findPorts(eliminate_duplicates=True)   # returns ['/dev/ttyUSB0', '/dev/ttyUSB2', …]
print("Meshtastic ports:", ports)

if len(ports) == 1: # if only one port found, assume it's the defcon radio
    defconInterface = SerialInterface(ports[0])  # connect to the first port
    defconNode = defconInterface.localNode
    print("Connected to DEFCONnect node on port:", ports[0])
elif len(ports) == 2: # if two ports found, assume one is defcon and the other is default
    for port in ports:
        iface = SerialInterface(port)  # connect to each port
        node = iface.localNode
        if node.getChannelByName("DEFCONnect"):
            defconInterface = iface
            defconNode = node
            print("Connected to DEFCONnect node on port:", port)
        else:
            print("Connected to default node on port:", port)
            defaultInterface = iface
            defaultNode = node
else:
    print("Multiple or no Meshtastic devices found. Please check your connections.")


