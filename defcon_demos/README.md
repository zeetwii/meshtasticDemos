# Meshtastic Demos

This is a series of demonstration scripts and examples for using locally running LLMs and other AI models to make sensors and systems more accessible over the Meshtastic mesh network.  Some of these demos were originally created for DEFCON 333's AI Village, while others have been added later as I found new ideas or use cases.  

Each demo has its own subdirectory with a README file that explains how to set it up and use it.  Feel free to explore and modify the code as needed for your own projects!

## Background

Meshtastic is an open-source mesh network built on top of inexpensive LoRa devices.  Unlike a lot of other mesh networks, meshtastic meshes are dynamic, meaning that nodes can join and leave the mesh at any time without any special configuration, and all nodes act as routers to help pass messages along.  This makes meshtastic a great choice for ad-hoc networks in remote areas, emergency situations, or just for fun outdoor activities like hiking or camping.

One of the areas where myself and several others have been experimenting with is using meshtastic for remote sensor data collection and monitoring.  However, meshtastic is intended to be an offline mesh network, so just spaming a link to your github doesn't actually teach anyone how to use your sensor or system if they don't already know how to use it.  This is where locally running LLMs and AI models come in.  By running a local LLM on a raspberry pi or similar device, we can provide natural language instructions and explanations to users over the meshtastic network, making it much easier for them to understand how to use the sensors and systems connected to the mesh.

## Equipment Needed

All of these demos are designed to run on a raspberry pi 5 or similar device with at least 4GB of free RAM.  You will also need a Meshtastic-compatible device, of which there are many options.  The [Meshtastic Device List](https://meshtastic.org/docs/hardware/devices/) is a good place to start, you can also look through the list of maintained devices on the [web flasher](https://flasher.meshtastic.org) for a list of currently supported devices.

## Demos

### LLM Chatbot over Meshtastic

This demo was created for DEFCON 333's AI Village, and demonstrates how to set up a basic chatbot using a locally running LLM and a meshtastic device.  The LLM plays a custom version of a prompt injection game, similar to the one made popular by Lakera.  The link to the demo code is here: [promptGame](./promptGame/README.md)

### Hacker Tracker over Meshtastic

This demo was created for DEFCON 333's AI Village, and demonstrates how to set up a basic interactive calendar and event tracker using a locally running LLM and a meshtastic device.  The LLM is used to interpret user queries and provide information about upcoming events in a natural language format.  The link to the demo code is here: [hackerTracker](./hackerTracker/README.md)

### Camera Monitor over Meshtastic

This demo was created to show how to use a locally running LLM to provide information about camera feeds and images.  The LLM is used to interpret user queries and provide information about the images in a natural language format.  The link to the demo code is here: [cameraMonitor](./cameraNode/README.md)