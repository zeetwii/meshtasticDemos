import socket
HOST, PORT = "127.0.0.1", 30003      # SBS-1 text
with socket.create_connection((HOST, PORT)) as s, s.makefile() as f:
    for line in f:
        fields = line.strip().split(',')
        if fields[0] == "MSG" and fields[1] == "3":        # airborne position
            icao  = fields[4]
            lat   = fields[14]
            lon   = fields[15]
            print(icao, lat, lon)