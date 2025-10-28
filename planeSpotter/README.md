# Plane Spotter over Meshtastic

This demo was made to show how to use a locally running LLM to provide information about nearby aircraft using ADS-B data.  The LLM is used to interpret user queries and provide information about the aircraft in natural and plain language.  This was meant to show how adding local LLM models to existing sensors and data sources can make them more accessible to users who may not be familiar with the technical details of the data.

The ADS-B data is pulled from a local instance of [readsb](https://github.com/wiedehopf/adsb-scripts/wiki/Automatic-installation-for-readsb), which collects data from a connected ADS-B receiver (such as a RTL-SDR dongle) and provides a web interface for viewing the data.  The LLM queries the readsb database to get information about nearby aircraft and then formats that information into a natural language response.  This allows users on the Meshtastic network to ask questions like "What aircraft are nearby?" or "Tell me about the plane with the callsign ABC123" and get informative responses.

## Equipment Needed

All of these demos are designed to run on a raspberry pi 5 or similar device with at least 4GB of free RAM.  You will also need a Meshtastic-compatible device, of which there are many options.  The [Meshtastic Device List](https://meshtastic.org/docs/hardware/devices/) is a good place to start, you can also look through the list of maintained devices on the [web flasher](https://flasher.meshtastic.org) for a list of currently supported devices.

For this specific demo, you will also need an ADS-B receiver.  The most common and inexpensive option is to use a RTL-SDR dongle, which can be purchased for around $20-$30.  You will also need an appropriate antenna for receiving ADS-B signals, which can be anything from one of the default antennas RTL-SDRs and HackRFs ship with, or more expensive specialized antennas.  You can even use a [village badge](https://www.tindie.com/products/aero_village/aerospace-village-badge-for-dc28-fully-assembled/) from DEFCON if you have one!

## Setup Instructions

Follow the instructions to get readsb set up on your raspberry pi: [readsb Automatic installation for readsb](https://github.com/wiedehopf/adsb-scripts/wiki/Automatic-installation-for-readsb).  After that you should be able to access the readsb web interface at `http://<your-raspberry-pi-ip>/tar1090`.  Once you have that set up, you can proceed to set up the LLM and Meshtastic integration.

The code for this demo is located in the `planeSpotter` directory.  You will need to install the required Python packages, which can be done using pip:

```bash
pip install ollama meshtastic
```

You will also need to have an Ollama model set up for this demo.  The recommended model is `gemma3:latest`, but you can use any model that supports the required functionality.  Make sure to have the Ollama CLI installed and configured on your raspberry pi.