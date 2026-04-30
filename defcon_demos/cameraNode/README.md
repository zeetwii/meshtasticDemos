# Camera Node

This is an example of using a Raspberry Pi with a camera module as a Meshtastic node that can capture images and send the descriptions and details of those images over the Meshtastic mesh network using a locally running LLM.  This was made for DEFCON 33's AI Village to demonstrate how to use local AI models to enhance the functionality of Meshtastic nodes.

By default, Meshtastic is a text only mesh network, so sending images directly over the network is not feasible.  However, by using a locally running LLM, we can capture images with the camera module, analyze them, and send descriptive text messages about the images over the Meshtastic network.  This allows users on the mesh to get information about their surroundings without needing to send large image files.  In the case of DEFCON, this was used to let people watch the AI Village remotely by sending descriptions of what the camera saw.

## Setup Instructions

You will need to install the Ollama and Meshtastic Python libraries to run this demo. You can do this by running the following commands:

```bash
pip install ollama meshtastic
```

You will also need to have a Meshtastic device set up and connected to your Raspberry Pi or similar device. You can find instructions for setting up a Meshtastic device [here](https://meshtastic.org/docs/getting-started/).

You will also need to use an Ollama model that is capable of both image and text processing.  The `gemma3:4b` model is the one we used for this demo, but you can experiment with other models as well.  Note that image capable models may require more RAM and processing power, so make sure your device meets the requirements.

Once you have the necessary libraries installed and your Meshtastic device set up, you can run the cameraNode.py script to start the camera node. The script will capture images at regular intervals, analyze them using the LLM, and send descriptive messages over the Meshtastic network when prompted.