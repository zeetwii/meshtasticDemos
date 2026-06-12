# Grabs the latest MAC address list files from the IEEE and saves them locally

import os # needed for file handling
import requests # needed for HTTP requests


DOWNLOADS = [
    ("oui.csv",   "http://standards-oui.ieee.org/oui/oui.csv"),
    ("mam.csv",   "http://standards-oui.ieee.org/oui28/mam.csv"),
    ("oui36.csv", "http://standards-oui.ieee.org/oui36/oui36.csv"),
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}


def download_mac_files():
    """Downloads the three IEEE MAC registry CSV files, overwriting any existing copies."""

    print("Downloading MAC address registry files from IEEE...")
    for filename, url in DOWNLOADS:
        if os.path.exists(filename):
            os.remove(filename)
        print(f"  {filename}...", end=" ")
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        with open(filename, "wb") as f:
            f.write(response.content)
        print("done")
    print("MAC files up to date.")


if __name__ == "__main__":
    print("Welcome to the MAC address list downloader for the wifi scanner demo.")
    print("This tool will grab the 3 MAC registry lists from the publicly hosted IEEE site and download them locally.\n")
    download_mac_files()
