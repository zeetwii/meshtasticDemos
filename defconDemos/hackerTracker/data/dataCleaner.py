# Hacker Tracker Data Cleaner
# This script cleans the data from the Hacker Tracker CSV file by stripping HTML tags

import csv, re, html

TAG_RE = re.compile(r"<[^>]+>")

def strip_html(val):
    val = html.unescape(val)
    return TAG_RE.sub("", val).strip()

with open("dc33.csv", newline="", encoding="utf-8") as infile, \
     open("dc33_clean.csv", "w", newline="", encoding="utf-8") as outfile:
    
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames + ["description"]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        row["description"] = strip_html(row["desc"])
        writer.writerow(row)

print("All cleaned!")
