# WiFi Scanning over Meshtastic

This is a proof of concept demo that shows how to use a large language model (LLM) to share WiFi scanning data over a Meshtastic network.  Similar to the [planeSpotter demo](../planeSpotter/README.md), this example has the model being prompted by a WiFi scanning script to share information about nearby WiFi networks.  However, instead of just translating and summerizing the data, the LLM is also able to send alerts to users on the mesh if it detects certain conditions, such as a new network appearing or a certian MAC manufacturer being nearby.  This allows the nodes and mesh network to be used for RF reconnaissance and surveillance, which allows you to expand into things like wardriving and counter-UAS systems.  

## Why This Demo?

This is actually based on some of my old work back when I was in the DoD.  I used to play around a lot with making portable drone detection systems, and a constant problem in that space is how to share data from the drone detection sensors with other users in real time, especially in areas where there is no existing network infrastructure.  At the time, we didn't really have a choice but to use expensive and power hungry high bandwidth radios, but with the rise of low bandwidth mesh networks like Meshtastic, I thought it would be interesting to see if we could use a LLM to share useful information from WiFi scanning data over a mesh network.  We're focusing on using WiFi scanning data in this demo because it's easy for non-technical users to understand, and is still how a lot of drone detection systems work, but the same concept could be applied to other types of RF data as well.

Most commerical and hobbyist drones use WiFi for both control and video transmission, via the drone acting as a WiFi access point that the controller connects to.  This both lets the drone operator easily connect to the drone via their phone or other controller, and the drone manufacturer can use cheap and widely available WiFi modules for the drone's communication system.  This means that by scanning for specific WiFi networks or certain MAC address tied to drone manufacturers, you can potentially detect the presence of drones with just a simple WiFi adapter.  This detection method is the foundation of library and demodulation focused detection systems.  Note that this method of detection is easy to spoof, via techniques like [naruto](https://github.com/zeetwii/naruto), and is not effective against more advance drones that use other methods of communication, such as LTE or custom RF protocols.  However, it's still a useful technique for detecting cheaper and more common drones, and it's a good technique to demonstrate how to share RF reconnaissance data over a mesh network.

## Equipment Needed

All of these demos are designed to run on a raspberry pi 5 or similar device with at least 4GB of free RAM.  You will also need a Meshtastic-compatible device, of which there are many options.  The [Meshtastic Device List](https://meshtastic.org/docs/hardware/devices/) is a good place to start, you can also look through the list of maintained devices on the [web flasher](https://flasher.meshtastic.org) for a list of currently supported devices.

For this specific demo, you will also need a WiFi adapter that is compatible with the raspberry pi, and supports monitor mode for WiFi scanning.  I find the Panda Wireless dongles to be a good option for this, but there are many other options out there as well.  You will also need to have an Ollama model set up for this demo.  The recommended model is `gemma4:e2b`, but you can use any model that supports the required functionality.  Make sure to have the Ollama CLI installed and configured on your raspberry pi.

## Setup Instructions

These scripts require Python 3.  Check your version with:

```bash
python3 --version
```

**WiFi adapter setup:** You will need a WiFi adapter that supports monitor mode for this demo.  I used a Panda Wireless PAU0F, but there are many other options out there as well.  Follow the instructions for your specific adapter to get it set up and working on your raspberry pi.  

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

Note that this script needs to be run with sudo to access the WiFi adapter and change its mode and frequencies.  

```bash
sudo python3 wifiSpotter.py
```