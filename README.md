# Meshtastic Demos

This is a collection of projects and demonstration scripts for using locally running LLMs and other AI models to make sensors and systems more accessible over the Meshtastic mesh network.  Some of these demos were originally created for DEFCON 333's AI Village, while others have been added later as I found new ideas or use cases.

Each project has its own subdirectory with a README file that explains how to set it up and use it.  Feel free to explore and modify the code as needed for your own projects!

## Background

Meshtastic is an open-source mesh network built on top of inexpensive LoRa devices.  Unlike a lot of other mesh networks, meshtastic meshes are dynamic and self organizing, meaning that nodes can join and leave the mesh at any time without any special configuration, and all nodes act as routers to help pass messages along.  This makes meshtastic a great choice for ad-hoc networks in remote areas, emergency situations, or just for fun outdoor activities like hiking or camping.  

However, this adhoc nature presents an interesting challenge for anyone hosting tools or sensors on the mesh, since you cannot assume that everyone in range of your node will know how to use it, or even that it exists.  While you could try to write catch alls that spam links to your github or documentation, this is not a very friendly way to teach or interact with users on the mesh, and it doesn't really take advantage of the unique capabilities of meshtastic.  This is where locally running LLMs and AI models come in.  By running a local LLM on a raspberry pi or similar device, we can provide natural language instructions and explanations to users over the meshtastic network, making it much easier for them to understand how to use the sensors and systems connected to the mesh.  Basically the LLM acts as a translation layer to help users understand how to interact with the tools and sensors on the mesh, without needing to have any prior knowledge or experience with them.  This can be especially useful in situations where you want to provide information or services to a wide range of users, such as in an emergency situation or a public event.

The use of LLMs as a translation layer is called detraining, since it removes the need for users to be trained on how to use the tool or system it is connected to.  Allowing users to interact with your tools and sensors in a natural language format can also make them more accessible and user friendly, especially for those who may not be familiar with the technical details of how the tools and sensors work.  Additionally, using LLMs in this way can help to make your tools and sensors more discoverable on the mesh, since users can simply ask the LLM for information about what is available on the mesh and how to use it.

Technically, you could use cloud based LLMs for this purpose, but this would require an internet connection, which is not always available or desirable in the situations where meshtastic is most useful.  By running a local LLM on a raspberry pi or similar device, you can provide these capabilities without needing an internet connection, making it much more versatile and useful in a wider range of situations.

## Equipment Needed

For all of these demos, you will need a raspberry pi 5 or similar device with at least 4GB of free RAM.  You will also need a Meshtastic-compatible device, of which there are many options.  The [Meshtastic Device List](https://meshtastic.org/docs/hardware/devices/) is a good place to start, you can also look through the list of maintained devices on the [web flasher](https://flasher.meshtastic.org) for a list of currently supported devices.

Depending on the demo, you may also need additional sensors or peripherals, such as a camera, an ADS-B receiver, or a GPS module.  Each demo's README file will specify any additional equipment needed and provide instructions for setting it up.


## Projects

### DEFCON33 AI Village Demos

These demos were created for DEFCON 33 as a part of the AI Village, and act as fun proof of concepts for using locally running LLMs to make tools and sensors more accessible over the meshtastic mesh network.  The demos include a chatbot, an interactive calendar and event tracker, and a camera monitor.  The link to the demo code is here: [defconDemos](./defconDemos/README.md)

### Plane Spotter over Meshtastic

This demo was made to show how to use a locally running LLM to provide information about nearby aircraft using ADS-B data.  The LLM is used to interpret user queries and provide information about the aircraft in a natural language format.  The link to the demo code is here: [planeSpotter](./planeSpotter/README.md)

### Trigger Camera over Meshtastic

This demo shows how to use a locally running LLM to share images taken by a camera over a Meshtastic network.  The camera is triggered by a YOLO model whenever it sees an object of interest from the targets list in the config file.  The LLM is then passed the image, and summerizes it into a concise text message that is sent over the mesh.  This allows users on the Meshtastic network to get real-time data from a camera, even though the mesh itself only supports text messages.  The link to the demo code is here: [triggerCamera](./triggerCamera/README.md)