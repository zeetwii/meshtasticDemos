# Prompt Game

This is a simple game that allows the user to play a prompt injection game over meshtastic, where the user has to try and get the AI to reveal a secret word. The game is designed to be played over meshtastic, and the user can interact with the AI by sending messages to it. The AI will respond with hints and clues to help the user guess the secret word. The game is designed to be fun and engaging, and can be played by anyone with a meshtastic device.  This was heavily inspired by the [Gandalf Prompt Injection Game](https://gandalf.lakera.ai/baseline).  

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
python3 promptGame.py
```

The AI will listen for messages on the Meshtastic network and respond to user inputs.

## How to Play

To play the game, simply send messages to the Meshtastic device running the promptGame.py script. The AI will respond with hints and clues to help you guess the secret word. Try to get the AI to reveal the secret word by crafting your messages carefully!  To make things a bit easier, you can also solve the game 20 questions style, as each secret word is an endangered animal.