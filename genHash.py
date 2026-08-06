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


def upload_to_jsonblob(json_file):
    """
    Upload a JSON file to jsonblob.com.

    Returns
    -------
    str
        URL of the uploaded JSON blob.
    """

    with open(json_file, "rb") as f:
        response = requests.post(
            "https://jsonblob.com/api/jsonBlob",
            data=f,
            headers={"Content-Type": "application/json"},
            timeout=(10, 300),   # 10s connect, 5 min upload
        )

    response.raise_for_status()

    url = response.headers.get("Location")
    print(f"Uploaded: {url}")

    return url
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
daily_url = upload_to_jsonblob(daily_file)
# station_url = upload_to_jsonblob(station_master_file)