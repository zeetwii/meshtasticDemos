# config_helper.py
import sys
from pathlib import Path

import yaml
import questionary

import meshtastic
import meshtastic.serial_interface
import meshtastic.util
from meshtastic.protobuf import channel_pb2


def find_or_choose_port():
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
    if not path.exists():
        return {}
    with path.open() as f:
        return yaml.safe_load(f) or {}


def pick_channels(snap, existing):
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


def main():
    out_path = Path(sys.argv[1] if len(sys.argv) > 1 else "config.yaml")
    existing = load_existing(out_path)

    port = find_or_choose_port()
    print(f"Connecting to {port}...")
    snap = snapshot(port)
    print(f"Connected as {snap['local']['long_name']} ({snap['local']['id']})")
    print(f"Saw {len(snap['channels'])} channels and {len(snap['nodes'])} known nodes.\n")

    channels = pick_channels(snap, existing)
    contacts = pick_contacts(snap, existing)

    # Preserve any project-specific keys the user added by hand (model, prompts, etc.)
    cfg = dict(existing)
    cfg["device"] = {"id": snap["local"]["id"], "long_name": snap["local"]["long_name"]}
    cfg["channels"] = channels
    cfg["contacts"] = contacts

    if out_path.exists() and not questionary.confirm(f"Overwrite {out_path}?", default=True).ask():
        print("Aborted.")
        return

    with out_path.open("w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    print(f"Wrote {out_path}.")


if __name__ == "__main__":
    main()