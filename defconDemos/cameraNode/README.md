# Camera Node

This is an example of using a Raspberry Pi with a camera module as a Meshtastic node that can capture images and send the descriptions and details of those images over the Meshtastic mesh network using a locally running LLM.  This was made for DEFCON 33's AI Village to demonstrate how to use local AI models to enhance the functionality of Meshtastic nodes.

By default, Meshtastic is a text only mesh network, so sending images directly over the network is not feasible.  However, by using a locally running LLM, we can capture images with the camera module, analyze them, and send descriptive text messages about the images over the Meshtastic network.  This allows users on the mesh to get information about their surroundings without needing to send large image files.  In the case of DEFCON, this was used to let people watch the AI Village remotely by sending descriptions of what the camera saw.

## Setup Instructions

These scripts require Python 3.  Check your version with:

```bash
python3 --version
```

Install the required Python packages:

```bash
pip install ollama meshtastic
```

Install Ollama on your Raspberry Pi if you haven't already:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

This demo requires an Ollama model that supports both image and text processing.  Image-capable models use more RAM than text-only models — check that you have at least 4GB free before pulling:

```bash
free -h
ollama pull gemma3:4b
```

Connect your Meshtastic radio to the Raspberry Pi over USB.  It will appear as a serial port, typically `/dev/ttyACM0` or `/dev/ttyUSB0`.  You can confirm which port with:

```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

The meshtastic Python library will automatically detect the device on the most likely port.  If it can't find it, you can pass the port explicitly — see the [Meshtastic Python API docs](https://python.meshtastic.org/) for details.

You will also need a camera connected to your Raspberry Pi.  A USB webcam or the Raspberry Pi Camera Module both work.  If you're using the Camera Module, make sure it is enabled in `raspi-config` under Interface Options.

Once everything is set up, run the script:

```bash
python3 cameraNode.py
```

The script will capture images at regular intervals, analyze them using the LLM, and send descriptive messages over the Meshtastic network when prompted.