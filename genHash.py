"""
hash is created and acolumn is added to copy of bala's working excel ->
two json be created station_master.json and rainfall<today>.json
"""
import pandas as pd
import hashlib
import datetime
import shutil

bala_src = r"Y:\Saurabh - SASD\Rainfall_Data_July_2026.xlsx"
bala_dst = r"C:\Users\NESAC\balaAWS"

shutil.copy(bala_src, bala_dst)

stationData = pd.read_csv('aws_location_cleaned.csv')
print (stationData.columns)
bala = pd.read_excel('Rainfall_Data_July_2026.xlsx')
def normalise(value):
    return (str(value).strip().upper().replace(' ','_'))

def stationID(row):
    key = "|".join([
        normalise(row['STATE']),
        normalise(row['DISTRICT']),
        normalise(row['STATION']),
        normalise(row['TYPE'])
    ])
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

stationData['stationID'] = stationData.apply(stationID, axis=1)

# print(bala.head())
print(f'generating master JSON ...')
stationData.to_json('station_master.json', orient='records')

bala['stationID'] = stationData.apply(stationID, axis=1)
print(bala.head())
metadata = [
    "stationID",
    "STATE",
    "DISTRICT",
    "STATION",
    "TYPE",
]

date = datetime.date.today()
# All columns whose names look like dates
date_columns = bala.columns[9:]     # assuming rainfall starts at column 9

rainfall = bala.melt(
    id_vars=metadata,
    value_vars=date_columns,
    var_name="date",
    value_name="rainfall"
)

print(rainfall.head())


rainfall.to_json(
    f"rainfall_{date}.json",
    orient="records",
    indent=4
)

# today = datetime.date.today().strftime("%-m/%-d/%Y")   # Linux
# yesterday = (date.today() - datetime.timedelta(days=1)).strftime("%#m/%#d/%Y")

# daily = bala[metadata + [yesterday]].rename(
#     columns={yesterday: "rainfall"}
# )

today = pd.Timestamp.today().normalize()  # Windows
yesterday = pd.Timestamp.today().normalize() - pd.Timedelta(days=1)

daily = bala[metadata + [yesterday]].rename(
    columns={yesterday: "rainfall"}
)

# daily = bala[metadata + [today]].rename(
#     columns={today: "rainfall"}
# )
print(daily)

