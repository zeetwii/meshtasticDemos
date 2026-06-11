from scapy.all import get_if_list, conf

# Print all available interfaces
print(get_if_list())

# Print detailed interface info
for iface_name, iface_obj in conf.ifaces.items():
    print(f"Name: {iface_name} | MAC: {iface_obj.mac}")
