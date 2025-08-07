#!/usr/bin/env bash
# install.sh – set up My Python App as a systemd service
# Run with:  bash install.sh
# Requires: sudo privileges (writes to /etc/systemd)

set -euo pipefail

RUNUSER="$(id -un)"      # e.g. pi
RUNGROUP="$(id -gn)"     # e.g. pi

Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$USER/.Xauthority

SERVICE_NAME="promptGame"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_BIN="/usr/bin/python3"          # adjust if you need python2
APP_ENTRY="${APP_DIR}/promptGame.py"      # adjust if your main file differs
LOG_DIR="/var/log/${SERVICE_NAME}"

echo "→ Creating log directory ${LOG_DIR}"
sudo mkdir -p "${LOG_DIR}"
sudo chown "${RUNUSER}:${RUNGROUP}" "${LOG_DIR}"


echo "→ Writing systemd service to ${SERVICE_FILE}"
sudo tee "${SERVICE_FILE}" >/dev/null <<EOF
[Unit]
Description=Prompt Game Service
After=network-online.target display-manager.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/python3 -u ${APP_ENTRY}
User=${RUNUSER}
Group=${RUNGROUP}
Environment=DISPLAY=:0
Restart=on-failure
RestartSec=5
StandardOutput=append:/var/log/${SERVICE_NAME}/stdout.log
StandardError=append:/var/log/${SERVICE_NAME}/stderr.log

[Install]
WantedBy=graphical.target
EOF

echo "→ Reloading systemd, enabling, and starting service"
sudo systemctl daemon-reload
sudo systemctl enable --now "${SERVICE_NAME}.service"

echo "✔ Done.  Check status with:
  sudo systemctl status ${SERVICE_NAME}
Follow live logs with:
  journalctl -u ${SERVICE_NAME} -f
Log files live in ${LOG_DIR}/"