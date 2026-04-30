# Prompt Game

This is a simple game that allows the user to play a prompt injection game over meshtastic, where the user has to try and get the AI to reveal a secret word. The game is designed to be played over meshtastic, and the user can interact with the AI by sending messages to it. The AI will respond with hints and clues to help the user guess the secret word. The game is designed to be fun and engaging, and can be played by anyone with a meshtastic device.  This was heavily inspired by the [Gandalf Prompt Injection Game](https://gandalf.lakera.ai/baseline).  

## Setup Instructions

You will need to install Ollama and Meshtastic Python libraries to run this demo. You can do this by running the following commands:

```bash
pip install ollama meshtastic
``` 

You will also need to have a Meshtastic device set up and connected to your Raspberry Pi or similar device. You can find instructions for setting up a Meshtastic device [here](https://meshtastic.org/docs/getting-started/).

Once you have the necessary libraries installed and your Meshtastic device set up, you can run the promptGame.py script to start the game. The AI will listen for messages on the Meshtastic network and respond to user inputs.

## How to Play

To play the game, simply send messages to the Meshtastic device running the promptGame.py script. The AI will respond with hints and clues to help you guess the secret word. Try to get the AI to reveal the secret word by crafting your messages carefully!  To make things a bit easier, you can also solve the game 20 questions style, as each secret word is an endangered animal.