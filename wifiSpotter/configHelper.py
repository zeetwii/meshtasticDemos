import sys # needed for command-line arguments
from pathlib import Path # needed for path processing

from macUpdater import download_mac_files # needed for updating MAC address files

import yaml # needed to read and write YAML files
import questionary # needed for multiple choice selections
from scapy.all import get_if_list # needed for OS-neutral interface enumeration

import meshtastic # needed for Meshtastic functionality
import meshtastic.serial_interface # needed for meshtastic serial interface
import meshtastic.util # needed for meshtastic utility functions
from meshtastic.protobuf import channel_pb2 # needed for meshtastic stuff

import ollama # needed for using Ollama to host models


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


def pick_wifi_interface(existing):
    """
    Lists available network interfaces and prompts the user to select which one
    the WiFi scanner should use.

    Args:
        existing (dict): The existing configuration data (used to pre-select the current interface).

    Returns:
        str: The selected interface name, or None if none are available.
    """

    interfaces = get_if_list()
    if not interfaces:
        print("No network interfaces found. Skipping WiFi interface selection.")
        return existing.get("wifi_interface")

    current = existing.get("wifi_interface")
    default = current if current in interfaces else interfaces[0]

    return questionary.select(
        "Which interface should the WiFi scanner use?",
        choices=interfaces,
        default=default,
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
    wifi_interface = pick_wifi_interface(existing)

    # Preserve any project-specific keys the user added by hand (prompts, etc.)
    cfg = dict(existing)
    cfg["device"] = {"id": snap["local"]["id"], "long_name": snap["local"]["long_name"]}
    cfg["channels"] = channels
    cfg["contacts"] = contacts
    cfg["checkin_interval_hours"] = checkin_interval
    if model:
        cfg["model"] = model
    cfg["disable_model_timeout"] = disable_model_timeout
    if wifi_interface:
        cfg["wifi_interface"] = wifi_interface

    if out_path.exists() and not questionary.confirm(f"Overwrite {out_path}?", default=True).ask():
        print("Aborted.")
        return

    with out_path.open("w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    print(f"Wrote {out_path}.")

    download_mac_files()


if __name__ == "__main__":
    main()