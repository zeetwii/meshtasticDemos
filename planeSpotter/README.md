# Plane Spotter

This is an example of how to let people interact with complex sensors over meshtastic.  Users can talk to the plane spotter in plain language and ask it about what planes are in the area, or what planes have been seen recently.  The plane spotter will respond with the relevant information based on ADS-B data it is receiving.  The software uses Ollama and a locally running LLM to process the user's requests and generate responses.  This entire project is designed to run on a Raspberry Pi, which is connected to a USB ADS-B receiver, and does not require an internet connection to run.

Install readsb: https://github.com/wiedehopf/adsb-scripts/wiki/Automatic-installation-for-readsb

