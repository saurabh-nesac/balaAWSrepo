#!/usr/bin/env python3
"""
Generate station hashes and rainfall JSONs.

Outputs:
    station_master.json
    rainfall_<latest_date>.json
    daily_rainfall_<latest_date>.json
"""

import hashlib
import shutil
from pathlib import Path

import pandas as pd
import json
import requests

import base64
import requests
import os

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
print(GITHUB_TOKEN)

# ---------------------------------------------------------------------
# GitHub Configuration
# ---------------------------------------------------------------------


OWNER = "saurabh-nesac"
REPO = "balaAWSrepo"
BRANCH = "main"

BASE_API = f"https://api.github.com/repos/{OWNER}/{REPO}/contents"

import base64
import requests

def upload_to_github(local_file, remote_path, archive=False):
    """
    Upload or update a file in GitHub.

    Parameters
    ----------
    local_file : Path
        Local file.

    remote_path : str
        Path of the latest file in GitHub.

    archive : bool
        If True, also upload a dated copy under archive/.
    """

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    with open(local_file, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    def put_file(path):
        url = f"{BASE_API}/{path}"

        # Check whether file exists
        r = requests.get(
            url,
            headers=headers,
            params={"ref": BRANCH},
            timeout=30,
        )

        sha = None

        if r.status_code == 200:
            sha = r.json()["sha"]
            action = "Updating"

        elif r.status_code == 404:
            action = "Creating"

        else:
            raise Exception(
                f"GitHub GET failed ({r.status_code})\n{r.text}"
            )

        print(f"{action}: {path}")

        payload = {
            "message": f"{action} {path}",
            "content": content,
            "branch": BRANCH,
        }

        if sha:
            payload["sha"] = sha

        r = requests.put(
            url,
            headers=headers,
            json=payload,
            timeout=120,
        )

        if r.status_code not in (200, 201):
            print(r.status_code)
            print(r.headers)
            print(r.text)

            raise Exception("Upload failed")

        print(
            "✓",
            f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/{path}",
        )

    # Upload latest copy
    put_file(remote_path)

    # Upload archive copy
    if archive:
        archive_path = f"archive/{local_file.name}"
        put_file(archive_path)
        
def upload_latest_and_archive(local_file, latest_name):
    """
    Upload one file twice:

    1. latest_name
    2. archive/original_filename
    """

    # latest copy
    upload_to_github(
        local_file,
        latest_name,
    )

    # archive copy
    upload_to_github(
        local_file,
        f"archive/{local_file.name}",
    )        
# ---------------------------------------------------------------------
# FILE PATHS
# ---------------------------------------------------------------------

bala_src = r"Y:\Saurabh - SASD\Rainfall_Data_August_2026.xlsx"

working_dir = Path(r"C:\Users\NESAC\balaAWS")
working_dir.mkdir(exist_ok=True)

excel_name = Path(bala_src).name
bala_dst = working_dir / excel_name

# Copy latest file
shutil.copy2(bala_src, bala_dst)

# ---------------------------------------------------------------------
# READ FILES
# ---------------------------------------------------------------------

stationData = pd.read_csv(working_dir / "aws_location_cleaned.csv")

bala = pd.read_excel(bala_dst)

print("Station master columns:")
print(stationData.columns)

print("\nRainfall Excel columns:")
print(bala.columns)

# ---------------------------------------------------------------------
# HASH FUNCTIONS
# ---------------------------------------------------------------------


def normalise(value):
    if pd.isna(value):
        return ""
    return str(value).strip().upper().replace(" ", "_")


def stationID(row):
    key = "|".join(
        [
            normalise(row["STATE"]),
            normalise(row["DISTRICT"]),
            normalise(row["STATION"]),
            normalise(row["TYPE"]),
        ]
    )

    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------
# CREATE HASHES
# ---------------------------------------------------------------------

stationData["stationID"] = stationData.apply(stationID, axis=1)
bala["stationID"] = bala.apply(stationID, axis=1)

# ---------------------------------------------------------------------
# SAVE STATION MASTER
# ---------------------------------------------------------------------

print("\nGenerating station_master.json...")

stationData.to_json(
    working_dir / "station_master.json",
    orient="records",
    indent=4,
)

# ---------------------------------------------------------------------
# METADATA COLUMNS
# ---------------------------------------------------------------------

metadata = [
    "stationID",
    "STATE",
    "DISTRICT",
    "STATION",
    "TYPE",
]

# Rainfall starts after TIME (UTC)
from datetime import datetime

date_columns = [
    c for c in bala.columns
    if isinstance(c, (pd.Timestamp, datetime))
]

print("Date Columns:")
print(date_columns)
# Ensure datetime columns
date_columns = pd.to_datetime(date_columns)

print(f"\nFound {len(date_columns)} rainfall days.")
print("First:", date_columns[0])
print("Last :", date_columns[-1])

# ---------------------------------------------------------------------
# LONG FORMAT RAINFALL JSON
# ---------------------------------------------------------------------

rainfall = bala.melt(
    id_vars=metadata,
    value_vars=date_columns,
    var_name="date",
    value_name="rainfall",
)

rainfall["date"] = pd.to_datetime(rainfall["date"]).dt.strftime("%Y-%m-%d")

latest_date = max(date_columns)

rainfall_file = (
    working_dir
    / f"rainfall_{latest_date.strftime('%Y-%m-%d')}.json"
)

print(f"\nWriting {rainfall_file.name}")

rainfall.to_json(
    rainfall_file,
    orient="records",
    indent=4,
)

rainfall.to_json(
    rainfall_file,
    orient="records",
    indent=4,
)
# ---------------------------------------------------------------------
# DAILY JSON
# ---------------------------------------------------------------------

yesterday = (
    pd.Timestamp.today().normalize() - pd.Timedelta(days=1)
).to_pydatetime()

available_dates = list(date_columns)

if yesterday in available_dates:
    selected_date = yesterday
    print("\nYesterday's data found.")
else:
    selected_date = max(available_dates)
    print("\nYesterday not available.")
    print("Using latest available:", selected_date.date())

daily = (
    bala[metadata + [selected_date]]
    .rename(columns={selected_date: "rainfall"})
)

daily["date"] = selected_date.strftime("%Y-%m-%d")

daily_file = (
    working_dir
    / f"daily_rainfall_{selected_date.strftime('%Y-%m-%d')}.json"
)

print(f"Writing {daily_file.name}")

daily.to_json(
    daily_file,
    orient="records",
    indent=4,
)

# ---------------------------------------------------------------------
# DONE
# ---------------------------------------------------------------------

print("\nDone.")
print(f"Station JSON : station_master.json")
print(f"Rainfall JSON: {rainfall_file.name}")
print(f"Daily JSON   : {daily_file.name}")

# rainfall_url = upload_to_jsonblob(rainfall_file)
# daily_url = upload_to_jsonblob(daily_file)
# station_url = upload_to_jsonblob(working_dir / "station_master.json")
# station_url = upload_to_jsonblob(station_master_file)
print("\nUploading to GitHub...\n")

# Station master (only latest)
upload_to_github(
    working_dir / "station_master.json",
    "station_master.json",
)

# Rainfall
upload_latest_and_archive(
    rainfall_file,
    "rainfall_latest.json",
)

# Daily rainfall
upload_latest_and_archive(
    daily_file,
    "daily_latest.json",
)

print("\nGitHub upload complete.")