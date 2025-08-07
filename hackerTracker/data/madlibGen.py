import csv
import os
from collections import defaultdict
from pathlib import Path

# ---------- settings ----------
INFILE  = "dc33_clean.csv"        # your CSV path
OUTDIR  = Path("daily_summaries")   # folder to hold the text files
OUTDIR.mkdir(exist_ok=True)
# --------------------------------

sentences_by_day = defaultdict(list)

with open(INFILE, newline='', encoding="utf-8") as fh:
    reader = csv.DictReader(fh)        # columns: day,starttime,endtime,village,track,title,speaker,desc,description
    for row in reader:
        sentence = (
            f"From {row['starttime']} to {row['endtime']}, "
            f"{row['village']} is hosting {row['speaker']} to present "
            f"{row['title']}, which is about {row['description']}."
        )
        sentences_by_day[row["day"]].append(sentence)

# write one file per unique day
for day, lines in sentences_by_day.items():
    # sanitise the filename a bit (remove slashes etc.)
    safe_day = "".join(ch for ch in day if ch.isalnum() or ch in (" ", "_", "-")).strip()
    outpath = OUTDIR / f"{safe_day}.txt"
    with open(outpath, "w", encoding="utf-8") as f_out:
        f_out.write("\n".join(lines))

print(f"Wrote {len(sentences_by_day)} files to {OUTDIR.resolve()}")
