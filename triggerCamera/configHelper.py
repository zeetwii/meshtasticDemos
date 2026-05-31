import sys # needed for command-line arguments
from pathlib import Path # needed for path processing

import yaml # needed to read and write YAML files
import questionary # needed for multiple choice selections

import meshtastic # needed for Meshtastic functionality
import meshtastic.serial_interface # needed for meshtastic serial interface
import meshtastic.util # needed for meshtastic utility functions
from meshtastic.protobuf import channel_pb2 # needed for meshtastic stuff

import ollama # needed for using Ollama to host models

try:
    import tkinter as tk
    from tkinter import filedialog as tk_filedialog
    _TKINTER_AVAILABLE = True
except ImportError:
    _TKINTER_AVAILABLE = False


def find_or_choose_port():
    """
    Checks for any meshtastic devices connected, and if more than one asks the user to select one.

    Returns:
        str: The selected serial port path.
    """

    ports = meshtastic.util.findPorts()
    if len(ports) == 1:
        return ports[0]
    if not ports:
        print("No Meshtastic device found over USB.")
        print("Plug it in and close any other Meshtastic clients (web, phone) —")
        print("only one client can talk to the radio at a time.")
        sys.exit(1)
    return questionary.select("Multiple devices found, pick one:", choices=ports).ask()


def snapshot(port):
    """
    Gets all the meshtastic stats from a device connected to a given port

    Args:
        port (str): The serial port path to the Meshtastic device.

    Returns:
        dict: A dictionary containing the snapshot data.
    """

    iface = meshtastic.serial_interface.SerialInterface(devPath=port)
    try:
        local = iface.getNode("^local")
        me = iface.getMyUser() or {}

        channels = []
        for ch in local.channels:
            if ch.role == channel_pb2.Channel.Role.DISABLED:
                continue
            channels.append({
                "index": ch.index,
                "name": ch.settings.name or ("LongFast" if ch.index == 0 else f"Ch{ch.index}"),
            })

        nodes = []
        for n in iface.nodes.values():
            user = n.get("user", {})
            if not user.get("id"):
                continue
            nodes.append({
                "id": user["id"],
                "long_name": user.get("longName") or "(unknown)",
                "short_name": user.get("shortName") or "????",
                "last_heard": n.get("lastHeard") or 0,
                "is_self": user["id"] == me.get("id"),
            })
        nodes.sort(key=lambda x: (-x["last_heard"], x["long_name"]))

        return {
            "local": {
                "id": me.get("id"),
                "long_name": me.get("longName"),
                "short_name": me.get("shortName"),
            },
            "channels": channels,
            "nodes": nodes,
        }
    finally:
        iface.close()


def load_existing(path):
    """
    Loads an existing configuration file.

    Args:
        path (Path): The path to the configuration file.

    Returns:
        dict: The loaded configuration data.
    """
    if not path.exists():
        return {}
    with path.open() as f:
        return yaml.safe_load(f) or {}


def pick_channels(snap, existing):
    """
    Selects which channels if any to use for admin purposes.

    Args:
        snap (dict): The snapshot data.
        existing (dict): The existing configuration data.

    Returns:
        list: A list of selected channels.
    """

    already = {c["index"] for c in existing.get("channels", [])}
    choices = [
        questionary.Choice(
            title=f"[{c['index']}] {c['name']}",
            value=c,
            checked=(c["index"] in already),
        )
        for c in snap["channels"]
    ]
    return questionary.checkbox(
        "Which channels should this project use?", choices=choices
    ).ask() or []


def pick_contacts(snap, existing):
    """
    Selects which contacts if any to use for admin purposes.

    Args:
        snap (dict): The snapshot data.
        existing (dict): The existing configuration data.

    Returns:
        list: A list of selected contacts.
    """

    already = {c["id"]: c.get("alias") for c in existing.get("contacts", [])}

    choices = []
    for n in snap["nodes"]:
        if n["is_self"]:
            continue
        title = f"{n['short_name']:<5}  {n['long_name']:<25}  {n['id']}"
        choices.append(questionary.Choice(title=title, value=n, checked=(n["id"] in already)))

    if not choices:
        print("\nNo other nodes in the NodeDB yet — leave the radio on the")
        print("mesh for a while and re-run to add contacts.\n")
        return []

    picked = questionary.checkbox(
        "Which nodes do you want to address by name in scripts?", choices=choices
    ).ask() or []

    contacts = []
    for n in picked:
        default_alias = already.get(n["id"]) or n["short_name"]
        alias = questionary.text(
            f"Alias for {n['long_name']} ({n['id']}):", default=default_alias
        ).ask()
        contacts.append({"id": n["id"], "alias": alias, "long_name": n["long_name"]})
    return contacts


def pick_checkin_interval(existing):
    """
    Asks how often the bot should check in, entered in hours.

    Args:
        existing (dict): The existing configuration data.

    Returns:
        float: The check-in interval in hours.
    """
    current = existing.get("checkin_interval_hours", 1)

    def validate_hours(val):
        try:
            v = float(val)
            if v > 0:
                return True
            return "Please enter a positive number."
        except ValueError:
            return "Please enter a valid number (e.g. 1, 0.5, 24)."

    result = questionary.text(
        "How often should the bot check in? (in hours — e.g. 1 = hourly, 24 = daily):",
        default=str(current),
        validate=validate_hours,
    ).ask()

    return float(result) if result is not None else current


def pick_model(existing):
    """
    Lists locally installed Ollama models and prompts the user to select one.

    Args:
        existing (dict): The existing configuration data (used to pre-select the current model).

    Returns:
        str: The selected model name, or None if no models are found.
    """
    try:
        models = ollama.list().models
    except Exception as e:
        print(f"Warning: could not reach Ollama ({e}). Skipping model selection.")
        return existing.get("model")

    if not models:
        print("No Ollama models installed. Run 'ollama pull <model>' to add one.")
        return existing.get("model")

    names = [m.model for m in models]
    current = existing.get("model")
    default = current if current in names else names[0]

    return questionary.select(
        "Which Ollama model should this project use?",
        choices=names,
        default=default,
    ).ask()


def pick_yolo_model_path(existing):
    """
    Prompts the user to select a local YOLO model file via a file dialog (or
    manual text entry if tkinter is unavailable).

    Args:
        existing (dict): The existing configuration data.

    Returns:
        str: The absolute path to the selected YOLO model file, or the existing
             value if the user cancels.
    """
    current = existing.get("yolo_model_path", "")

    if _TKINTER_AVAILABLE:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        chosen = tk_filedialog.askopenfilename(
            title="Select your YOLO model file",
            filetypes=[
                ("YOLO model files", "*.pt *.onnx *.torchscript *.tflite *.pb"),
                ("All files", "*.*"),
            ],
            initialfile=current if current else None,
        )
        root.destroy()
        if chosen:
            return str(Path(chosen).resolve())
        # User cancelled the dialog — fall through to text prompt
        print("No file selected in dialog, falling back to text entry.")

    def validate_path(val):
        if not val.strip():
            return "Path cannot be empty."
        if not Path(val.strip()).is_file():
            return f"File not found: {val.strip()}"
        return True

    result = questionary.text(
        "Path to YOLO model file (.pt, .onnx, ...):",
        default=current,
        validate=validate_path,
    ).ask()

    return str(Path(result.strip()).resolve()) if result else current


def pick_yolo_trigger_classes(model_path, existing):
    """
    Loads the YOLO model at model_path with ultralytics to enumerate its class
    names, then lets the user pick which classes should act as camera triggers.

    Args:
        model_path (str): Path to the YOLO model file.
        existing (dict): The existing configuration data.

    Returns:
        list[str]: The selected class name strings.
    """
    if not model_path:
        print("No YOLO model path set — skipping trigger class selection.")
        return existing.get("yolo_trigger_classes", [])

    try:
        from ultralytics import YOLO
        model = YOLO(model_path)
        class_names = list(model.names.values())
    except Exception as e:
        print(f"Warning: could not load YOLO model ({e}). Skipping trigger class selection.")
        return existing.get("yolo_trigger_classes", [])

    already = set(existing.get("yolo_trigger_classes", []))
    choices = [
        questionary.Choice(title=name, value=name, checked=(name in already))
        for name in class_names
    ]
    selected = questionary.checkbox(
        "Which detected object classes should trigger the camera?",
        choices=choices,
    ).ask()
    return selected if selected is not None else list(already)


def pick_yolo_confidence(existing):
    """
    Prompts the user to enter a YOLO detection confidence threshold (0.0–1.0).
    A higher value (e.g. 0.75) reduces false positives; lower values catch
    more detections at the risk of noise.

    Args:
        existing (dict): The existing configuration data.

    Returns:
        float: The chosen confidence threshold.
    """
    current = existing.get("yolo_confidence", 0.75)

    def validate_conf(val):
        try:
            v = float(val)
            if 0.0 < v <= 1.0:
                return True
            return "Please enter a value between 0 and 1 (exclusive)."
        except ValueError:
            return "Please enter a valid number (e.g. 0.75)."

    result = questionary.text(
        "YOLO detection confidence threshold (0–1). Higher values mean fewer false positives — 0.75 recommended for best results:",
        default=str(current),
        validate=validate_conf,
    ).ask()

    return float(result) if result is not None else current


def pick_trigger_cooldown(existing):
    """
    Asks how many seconds must pass between automatic trigger messages.

    Args:
        existing (dict): The existing configuration data.

    Returns:
        int: The cooldown period in seconds.
    """
    current = existing.get("trigger_cooldown_seconds", 60)

    def validate_seconds(val):
        try:
            v = int(val)
            if v >= 0:
                return True
            return "Please enter a non-negative integer."
        except ValueError:
            return "Please enter a whole number of seconds (e.g. 60)."

    result = questionary.text(
        "Minimum seconds between automatic trigger messages (0 = no cooldown):",
        default=str(current),
        validate=validate_seconds,
    ).ask()

    return int(result) if result is not None else current


def pick_model_timeout(existing):
    """
    Asks whether to disable Ollama's model timeout.

    Args:
        existing (dict): The existing configuration data.

    Returns:
        bool: True if the model timeout should be disabled, False otherwise.
    """
    current = existing.get("disable_model_timeout", False)
    return questionary.confirm(
        "Disable Ollama's model timeout?",
        default=current,
    ).ask()


def main():
    """
    The main entry point for the configuration helper.

    """

    out_path = Path(sys.argv[1] if len(sys.argv) > 1 else "config.yaml")
    existing = load_existing(out_path)

    port = find_or_choose_port()
    print(f"Connecting to {port}...")
    snap = snapshot(port)
    print(f"Connected as {snap['local']['long_name']} ({snap['local']['id']})")
    print(f"Saw {len(snap['channels'])} channels and {len(snap['nodes'])} known nodes.\n")

    channels = pick_channels(snap, existing)
    contacts = pick_contacts(snap, existing)
    checkin_interval = pick_checkin_interval(existing)
    model = pick_model(existing)
    disable_model_timeout = pick_model_timeout(existing)
    trigger_cooldown = pick_trigger_cooldown(existing)
    yolo_model_path = pick_yolo_model_path(existing)
    yolo_trigger_classes = pick_yolo_trigger_classes(yolo_model_path, existing)
    yolo_confidence = pick_yolo_confidence(existing)

    # Preserve any project-specific keys the user added by hand (prompts, etc.)
    cfg = dict(existing)
    cfg["device"] = {"id": snap["local"]["id"], "long_name": snap["local"]["long_name"]}
    cfg["channels"] = channels
    cfg["contacts"] = contacts
    cfg["checkin_interval_hours"] = checkin_interval
    if model:
        cfg["model"] = model
    cfg["disable_model_timeout"] = disable_model_timeout
    cfg["trigger_cooldown_seconds"] = trigger_cooldown
    if yolo_model_path:
        cfg["yolo_model_path"] = yolo_model_path
    cfg["yolo_trigger_classes"] = yolo_trigger_classes
    cfg["yolo_confidence"] = yolo_confidence

    if out_path.exists() and not questionary.confirm(f"Overwrite {out_path}?", default=True).ask():
        print("Aborted.")
        return

    with out_path.open("w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    print(f"Wrote {out_path}.")


if __name__ == "__main__":
    main()