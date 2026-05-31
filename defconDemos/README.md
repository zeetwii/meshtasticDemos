# Meshtastic Demos

This is a series of demonstration scripts and examples for using locally running LLMs and other AI models to make sensors and systems more accessible over the Meshtastic mesh network.  Some of these demos were originally created for DEFCON 333's AI Village, while others have been added later as I found new ideas or use cases.  

Each demo has its own subdirectory with a README file that explains how to set it up and use it.  Feel free to explore and modify the code as needed for your own projects!

## Background

Meshtastic is an open-source mesh network built on top of inexpensive LoRa devices.  Unlike a lot of other mesh networks, meshtastic meshes are dynamic, meaning that nodes can join and leave the mesh at any time without any special configuration, and all nodes act as routers to help pass messages along.  This makes meshtastic a great choice for ad-hoc networks in remote areas, emergency situations, or just for fun outdoor activities like hiking or camping.

One of the areas where myself and several others have been experimenting with is using meshtastic for remote sensor data collection and monitoring.  However, meshtastic is intended to be an offline mesh network, so just spaming a link to your github doesn't actually teach anyone how to use your sensor or system if they don't already know how to use it.  This is where locally running LLMs and AI models come in.  By running a local LLM on a raspberry pi or similar device, we can provide natural language instructions and explanations to users over the meshtastic network, making it much easier for them to understand how to use the sensors and systems connected to the mesh.

## Equipment Needed

All of these demos are designed to run on a raspberry pi 5 or similar device with at least 4GB of free RAM.  You will also need a Meshtastic-compatible device connected to the Raspberry Pi over USB serial — the scripts use a serial connection to communicate with the radio.  There are many compatible devices; the [Meshtastic Device List](https://meshtastic.org/docs/hardware/devices/) is a good place to start, and the [web flasher](https://flasher.meshtastic.org) lists all currently supported devices.  These demos were developed and tested using a [Seeed Studio XIAO ESP32S3 with SX1262 LoRa module](https://www.seeedstudio.com/Wio-SX1262-with-XIAO-ESP32S3-p-5982.html), but any Meshtastic-compatible device with a USB serial connection should work.

## Prerequisites

Before running any of the demos, make sure you have the following set up on your Raspberry Pi.

**Python 3:** All scripts require Python 3.  Check your version with:

```bash
python3 --version
```

If `pip` defaults to Python 2 on your system, use `pip3` in place of `pip` for all package install commands.

**Available RAM:** LLM models consume a significant amount of RAM.  Check how much you have free before starting:

```bash
free -h
```

**Ollama:** All of the demos use Ollama to run LLMs locally.  Install it on your Raspberry Pi with:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Each demo's README specifies which model to pull.

**Meshtastic Device:** When you plug in your Meshtastic radio over USB, it will appear as a serial port — typically `/dev/ttyACM0` or `/dev/ttyUSB0`.  Confirm which port your device is using with:

```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

If you haven't set up your Meshtastic device yet, follow the [Meshtastic Getting Started Guide](https://meshtastic.org/docs/getting-started/) before running any of these demos.

## Demos

### LLM Chatbot over Meshtastic

This demo was created for DEFCON 333's AI Village, and demonstrates how to set up a basic chatbot using a locally running LLM and a meshtastic device.  The LLM plays a custom version of a prompt injection game, similar to the one made popular by Lakera.  The link to the demo code is here: [promptGame](./promptGame/README.md)

### Hacker Tracker over Meshtastic

This demo was created for DEFCON 333's AI Village, and demonstrates how to set up a basic interactive calendar and event tracker using a locally running LLM and a meshtastic device.  The LLM is used to interpret user queries and provide information about upcoming events in a natural language format.  The link to the demo code is here: [hackerTracker](./hackerTracker/README.md)

### Camera Monitor over Meshtastic

This demo was created to show how to use a locally running LLM to provide information about camera feeds and images.  The LLM is used to interpret user queries and provide information about the images in a natural language format.  The link to the demo code is here: [cameraMonitor](./cameraNode/README.md)