# Plane Spotter over Meshtastic

This is a proof of concept demo that shows how to use a large language model (LLM) to provide information about nearby aircraft using ADS-B data, and then share that information over a Meshtastic network.  The idea is that users on the Meshtastic network can ask questions about nearby aircraft and get informative responses based on the ADS-B data collected by the local readsb instance.

The ADS-B data is pulled from a local instance of [readsb](https://github.com/wiedehopf/adsb-scripts/wiki/Automatic-installation-for-readsb), which collects data from a connected ADS-B receiver (such as a RTL-SDR dongle) and provides a web interface for viewing the data.  The LLM queries the readsb database to get information about nearby aircraft and then formats that information into a natural language response.  This allows users on the Meshtastic network to ask questions like "What aircraft are nearby?" or "Tell me about the plane with the callsign ABC123" and get informative responses.

## Why This Demo?

ADS-B is interesting as a data link, despite being a bit niche, because it has dozens of different decoders and collection sites that are regularly by everyone from casual travelers to aviation enthusiasts.  Many of these collection sites have global coverage, and easy to use web interfaces.  However these collection sites have shown to be vulnerable to bullying and censorship.  Years ago, Elon Musk got angry at several of these collection sites for showing the location of his private jet, and bullied them into adding an artifical 24 hour delay to the data for his jet.  He's stull broadcasting ADS-B data, and every sensor that picks up his jet can still see it live, but the public-facing web interfaces have been censored.  Hence, the need to show how multiple sensors on a Meshtastic network can be used to share this data without relying on a centralized hub that can be bullied or censored.

However, ADS-B data is transmitted roughly every quarter to half second, and some of the packets are too large to fit in a single Meshtastic message.  This is where it becomes a great demonstration of how LLMs can be used to summerize and format data in a way that can be easily shared over a low-bandwidth network like Meshtastic.  The LLM can take the raw ADS-B data, extract the relevant information, and then format it into a concise and informative message that can be sent over Meshtastic.  This allows users on the Meshtastic network to get real-time information about nearby aircraft without needing to access a web interface or rely on a centralized data source.  Additionally, since the LLM is acting as an interface, users on the mesh don't need to worry about knowing field names or data formats, they can just ask natural language questions and get informative responses.

## Equipment Needed

All of these demos are designed to run on a raspberry pi 5 or similar device with at least 4GB of free RAM.  You will also need a Meshtastic-compatible device, of which there are many options.  The [Meshtastic Device List](https://meshtastic.org/docs/hardware/devices/) is a good place to start, you can also look through the list of maintained devices on the [web flasher](https://flasher.meshtastic.org) for a list of currently supported devices.

For this specific demo, you will also need an ADS-B receiver.  The most common and inexpensive option is to use a RTL-SDR dongle, which can be purchased for around $20-$30.  You will also need an appropriate antenna for receiving ADS-B signals, which can be anything from one of the default antennas RTL-SDRs and HackRFs ship with, or more expensive specialized antennas.  You can even use a [village badge](https://www.tindie.com/products/aero_village/aerospace-village-badge-for-dc28-fully-assembled/) from DEFCON if you have one!

## Setup Instructions

These scripts require Python 3.  Check your version with:

```bash
python3 --version
```

**RTL-SDR setup:** Before installing readsb, you need to prevent the default DVB-T kernel module from claiming the RTL-SDR dongle.  Run the following, then reboot:

```bash
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/blacklist-rtl.conf
sudo reboot
```

**readsb:** Follow the instructions to get readsb set up on your Raspberry Pi: [readsb Automatic installation](https://github.com/wiedehopf/adsb-scripts/wiki/Automatic-installation-for-readsb).  After setup you should be able to access the readsb web interface at `http://<your-raspberry-pi-ip>/tar1090` and see aircraft being tracked.

**Python packages:**

```bash
pip install -r requirements.txt
```

**Ollama:** Install Ollama if you haven't already:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Pull the recommended model (check you have at least 4GB free RAM first with `free -h`):

```bash
ollama pull gemma4:e2b
```

**Meshtastic device:** Connect your Meshtastic radio to the Raspberry Pi over USB.  It will appear as a serial port, typically `/dev/ttyACM0` or `/dev/ttyUSB0`.  You can confirm which port with:

```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

**Configuration:** [configHelper.py](./configHelper.py) is a helper script that generates a config file for this demo.  Run it and follow the prompts:

```bash
python3 configHelper.py
```

It will ask for your Meshtastic device's node ID, the Ollama model name, and how often you want the system to send check-in messages.

**Run the demo:**

```bash
python3 planeSpotter.py
```