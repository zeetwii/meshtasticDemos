# Trigger Camera over Meshtastic

This is a proof of concept demo that shows how to use a large language model (LLM) to share images taken by a camera over a Meshtastic network.  Unlike the defcon camera demo, this example has the model being prompted by a YOLO model to take a picture whenever it sees an object of interest from the targets list in the config file.  The LLM is then passed the image, and summerizes it into a concise text message that is sent over the mesh.  This allows users on the Meshtastic network to get real-time data from a camera, even though the mesh itself only supports text messages.  

Note that yes, this is basically an open source flock camera on a mesh, so please don't use it to violate anyone's privacy or break any laws.  

## Why This Demo?

This demo started as an ask from a friend, who was interested in setting up a camera that could be triggered by certain objects, and then share the images over a Meshtastic network.  The idea was that the camera could be set up in a remote location, and then whenever it saw something interesting (like a car, or a person), it would take a picture and share it with the rest of the mesh.  This would allow users on the mesh to get real-time updates about what was happening in that location, without needing to rely on a high bandwidth connection or a centralized server.

## Equipment Needed

All of these demos are designed to run on a raspberry pi 5 or similar device with at least 4GB of free RAM.  You will also need a Meshtastic-compatible device, of which there are many options.  The [Meshtastic Device List](https://meshtastic.org/docs/hardware/devices/) is a good place to start, you can also look through the list of maintained devices on the [web flasher](https://flasher.meshtastic.org) for a list of currently supported devices.

For this specific demo, you will also need a camera that is compatible with the raspberry pi, such as a USB webcam.  You will also need to have a YOLO model set up for object detection, which can be done using a pre-trained model or by training your own model on a custom dataset.  Finally, you will need to have an Ollama model set up for this demo.  The recommended model is `gemma4:e2b`, but you can use any model that supports the required functionality.  Make sure to have the Ollama CLI installed and configured on your raspberry pi.

## Setup Instructions

These scripts require Python 3.  Check your version with:

```bash
python3 --version
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Install Ollama if you haven't already:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Pull the recommended model (check you have at least 4GB free RAM first with `free -h`):

```bash
ollama pull gemma4:e2b
```

Connect your Meshtastic radio to the Raspberry Pi over USB.  It will appear as a serial port, typically `/dev/ttyACM0` or `/dev/ttyUSB0`.  You can confirm which port with:

```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

Connect your USB webcam.  You can verify the camera is detected by checking for `/dev/video0` or running `v4l2-ctl --list-devices`.

**Configuration:** [configHelper.py](./configHelper.py) is a helper script that generates a config file for this demo.  Run it and follow the prompts:

```bash
python3 configHelper.py
```

It will ask for your Meshtastic device's node ID, the Ollama and YOLO model names, the list of target objects that should trigger the camera (e.g. `car`, `person`), and how often you want the system to send check-in messages.

**Run the demo:**

```bash
python3 triggerCamera.py
```

Whenever the YOLO model detects an object of interest, it will trigger the camera to capture an image.  The LLM will then process the image and send a summary message over the mesh.