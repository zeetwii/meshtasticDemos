import cv2 # needed for camera capture and image encoding
import threading # needed to run the camera capture on a background thread
import time # needed for timing trigger cooldowns and check-in intervals
import os # needed for file path handling
import yaml # needed to read configuration from a YAML file
import textwrap # needed to wrap long messages for Meshtastic
import base64 # needed to encode images for Ollama

from ultralytics import YOLO # needed to load the YOLO model and run predictions
from meshtastic.serial_interface import SerialInterface # needed to connect to the Meshtastic device and send/receive messages
from meshtastic.util import findPorts # needed to find available serial ports for Meshtastic devices
import meshtastic # needed for pubsub to subscribe to Meshtastic events
from pubsub import pub # needed for pubsub to subscribe to Meshtastic events
import ollama # needed to interact with the Ollama API for vision model inference


class LatestFrameCapture:
    """
    Runs camera capture on a background thread, always keeping only the
    most recent frame. The main thread never blocks waiting on a stale
    buffer, it just reads whatever arrived last.
    """

    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.lock = threading.Lock()
        self.frame = None
        self.running = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self):
        while self.running:
            ok, frame = self.cap.read()
            if ok:
                with self.lock:
                    self.frame = frame

    def read(self):
        with self.lock:
            return self.frame is not None, (self.frame.copy() if self.frame is not None else None)

    def release(self):
        self.running = False
        self._thread.join()
        self.cap.release()


class TriggerCamera:
    """
    Connects a YOLO-monitored camera to a Meshtastic network. When YOLO
    detects an object in the configured trigger list, an Ollama vision model
    describes the scene and the summary is broadcast over the mesh.
    """

    # Minimum seconds between automatic trigger messages to avoid flooding the mesh
    TRIGGER_COOLDOWN = 60

    def __init__(self):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        self.model = config.get('model', 'gemma3:latest')
        self.channels = config.get('channels', [])
        self.contacts = config.get('contacts', [])
        self.device_id = config.get('device', {}).get('id')
        self.keep_alive = -1 if config.get('disable_model_timeout', False) else None
        self.checkin_interval = config.get('checkin_interval_hours') or 0

        yolo_model_path = config.get('yolo_model_path', 'yolo11n.pt')
        self.trigger_classes = [c.lower() for c in config.get('yolo_trigger_classes', [])]
        self.yolo_confidence = config.get('yolo_confidence', 0.75)

        self._last_trigger_time = 0
        self._trigger_lock = threading.Lock()

        print("Starting camera...")
        self.camera = LatestFrameCapture(0)

        print(f"Loading YOLO model from {yolo_model_path}...")
        self.yolo = YOLO(yolo_model_path)

        # Subscribe before creating the interface — the connection.established event fires
        # during SerialInterface.__init__() from a background thread, so subscribing after
        # the constructor would always miss it.
        self.interface = None
        pub.subscribe(self.onReceive, "meshtastic.receive.text")
        pub.subscribe(self.onConnection, "meshtastic.connection.established")

        print("Initializing Trigger Camera Node...")
        ports = findPorts(eliminate_duplicates=True)

        if len(ports) == 0:
            print("No Meshtastic devices found. Please check your connections.")
            exit(1)
        elif len(ports) == 1:
            self.interface = SerialInterface(ports[0])
            print("Connected to Meshtastic node on port:", ports[0])
            print(f"Node ID: {self.interface.getMyNodeInfo()['user']['id']}")
        else:
            print(f"Multiple Meshtastic devices found. Looking for configured device {self.device_id}...")
            self.interface = None
            for port in ports:
                try:
                    iface = SerialInterface(port)
                    node_id = iface.getMyNodeInfo()['user']['id']
                    if node_id == self.device_id:
                        self.interface = iface
                        print(f"Connected to {self.device_id} on port {port}")
                        break
                    iface.close()
                except Exception as e:
                    print(f"Could not check port {port}: {e}")
            if self.interface is None:
                print(f"Device {self.device_id} not found among available ports. Please check your config.")
                exit(1)

        print(f"Preloading Ollama model ({self.model})...")
        response = ollama.chat(model=self.model, keep_alive=self.keep_alive, messages=[{'role': 'system', 'content': 'Say boot up successful'}])
        print(response.message.content)

    def onConnection(self, interface):
        """
        Callback for when the Meshtastic connection is established. Sends a
        startup message and kicks off the detection and check-in threads.
        """
        node_id = interface.getMyNodeInfo()['user']['id']
        if self.device_id and node_id != self.device_id:
            return

        self.interface = interface
        print("Meshtastic connection established.")
        startup_msg = "Trigger Camera online. Watching for: " + ", ".join(self.trigger_classes) + "."

        for channel in self.channels:
            idx = channel.get('index', 0)
            print(f"Sending startup message to channel {channel.get('name', idx)} (index {idx})")
            interface.sendText(startup_msg, channelIndex=idx)
            time.sleep(1)

        for contact in self.contacts:
            dest = contact.get('id')
            print(f"Sending startup message to contact {contact.get('alias', dest)}")
            interface.sendText(startup_msg, destinationId=dest)
            time.sleep(1)

        threading.Thread(target=self._detectionLoop, daemon=True).start()
        print("YOLO detection loop started.")

        if self.checkin_interval:
            threading.Thread(target=self._checkinLoop, daemon=True).start()
            print(f"Check-in thread started (every {self.checkin_interval}h)")

    def _detectionLoop(self):
        """
        Background thread: runs YOLO on every new camera frame and sends a
        mesh message whenever a trigger-class object is detected. Rate-limited
        by TRIGGER_COOLDOWN to avoid flooding the network.
        """
        while True:
            ok, frame = self.camera.read()
            if not ok:
                time.sleep(0.05)
                continue

            results = self.yolo.predict(frame, conf=self.yolo_confidence, verbose=False)
            detected = {
                results[0].names[int(cls)].lower()
                for cls in results[0].boxes.cls
            }
            triggered = detected & set(self.trigger_classes)

            if not triggered:
                continue

            now = time.time()
            with self._trigger_lock:
                if now - self._last_trigger_time < self.TRIGGER_COOLDOWN:
                    continue
                self._last_trigger_time = now

            print(f"Trigger detected: {triggered}")
            description = self._describeFrame(frame, list(triggered))
            if description:
                self._broadcast(description)

    def _checkinLoop(self):
        """
        Background thread that sends a periodic status message to all
        configured channels and contacts.
        """
        interval_seconds = self.checkin_interval * 3600
        while True:
            time.sleep(interval_seconds)
            msg = "Trigger Camera check-in: system running, monitoring for " + ", ".join(self.trigger_classes) + "."
            print("Sending scheduled check-in message...")
            self._broadcast(msg)

    def onReceive(self, packet, _):
        """
        Callback for incoming Meshtastic text messages. Responds to direct
        messages with a live description of the current camera view.
        """
        if packet['decoded']['portnum'] != 'TEXT_MESSAGE_APP':
            return

        if packet['to'] != self.interface.getMyNodeInfo()['num']:
            return

        if packet['from'] == self.interface.getMyNodeInfo()['num']:
            return

        print(f"User ID: {packet['from']} \nMessage: {packet['decoded']['text']}")

        ok, frame = self.camera.read()
        if not ok:
            self.interface.sendText("No camera frame available.", destinationId=packet['from'])
            return

        results = self.yolo.predict(frame, conf=self.yolo_confidence, verbose=False)
        detected = [results[0].names[int(cls)] for cls in results[0].boxes.cls]

        description = self._describeFrame(frame, detected)
        if not description:
            description = "Could not generate a description of the current scene."

        for line in textwrap.wrap(description, width=220):
            self.interface.sendText(line, destinationId=packet['from'])
            time.sleep(1)

    def _describeFrame(self, frame, detected_labels):
        """
        JPEG-encodes the frame, passes it to the Ollama vision model alongside
        the YOLO-detected labels, and returns a concise plain-text description
        suitable for a Meshtastic message.
        """
        ok, buf = cv2.imencode('.jpg', frame)
        if not ok:
            return None

        image_b64 = base64.b64encode(buf.tobytes()).decode('utf-8')
        label_str = ", ".join(detected_labels) if detected_labels else "unknown objects"

        messages = [
            {
                'role': 'system',
                'content': (
                    'You are an automated camera sensor node on a Meshtastic mesh network. '
                    'Describe the image in one or two concise sentences suitable for a text '
                    'message. Focus on the detected objects and any relevant context.'
                )
            },
            {
                'role': 'user',
                'content': f'The camera detected: {label_str}. Describe what you see.',
                'images': [image_b64]
            }
        ]

        try:
            response = ollama.chat(model=self.model, keep_alive=self.keep_alive, messages=messages)
            return response.message.content
        except Exception as e:
            print(f"Ollama error: {e}")
            return None

    def _broadcast(self, msg):
        """Send a message to all configured channels and contacts."""
        lines = textwrap.wrap(msg, width=220)
        for channel in self.channels:
            idx = channel.get('index', 0)
            for line in lines:
                self.interface.sendText(line, channelIndex=idx)
                time.sleep(1)
        for contact in self.contacts:
            dest = contact.get('id')
            for line in lines:
                self.interface.sendText(line, destinationId=dest)
                time.sleep(1)

    def shutdown(self):
        """Clean up the camera and Meshtastic interface."""
        self.camera.release()
        if self.interface:
            self.interface.close()


if __name__ == "__main__":
    node = TriggerCamera()
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("Shutting down Trigger Camera Node...")
        node.shutdown()
