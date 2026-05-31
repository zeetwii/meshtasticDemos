# Hacker Tracker demo

This is a demo that uses a downloaded copy of the hacker tracker data from the [Hacker Tracker](https://hackertracker.net/) website.  We then parse that data into a locally running LLM and allow anyone of the DEFCON Meshtastic network to query the data and get information about when and where different events and talks are happening.

The data is pulled from [DEFCON 33 Downloads](https://defcon.outel.org/dcwp/dc33/downloads/) and is updated manually.  So this is not a live feed of the data, but rather a snapshot of the data at the time of the download.

## Setup Instructions

These scripts require Python 3.  Check your version with:

```bash
python3 --version
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Install Ollama on your Raspberry Pi if you haven't already:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Pull the model used by this demo:

```bash
ollama pull gemma3:4b
```

Connect your Meshtastic radio to the Raspberry Pi over USB.  It will appear as a serial port, typically `/dev/ttyACM0` or `/dev/ttyUSB0`.  You can confirm which port with:

```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

Once everything is set up, run the script:

```bash
python3 hackerTracker.py
```

Users on the Meshtastic network can then send natural language queries about DEFCON 33 events and talks, and the LLM will respond with information from the downloaded schedule data.  Note that if you want to use this for a different event, you will need to replace the data files in the `data/` directory with data from that event.
