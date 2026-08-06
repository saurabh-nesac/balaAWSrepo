from datetime import datetime
import sys

import pandas as pd
from shapely.geometry import Point
import geopandas as gpd

start_date = sys.argv[1]
end_date = sys.argv[2]
start_dt = datetime.strptime(start_date, "%Y%m%d")
end_dt = datetime.strptime(end_date, "%Y%m%d")
YEAR = start_dt.year
MONTH = start_dt.month
MONTH_NAME = start_dt.strftime("%B").upper()  # JUNE
MONTH_TITLE = start_dt.strftime("%B")  # June
YEAR_MONTH = start_dt.strftime("%Y%m")

excel_file = r"Rainfall_Data_April_2026.xlsx"
df = pd.read_excel(excel_file)
print(df.columns)

df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")

df = df.dropna(subset=["LATITUDE", "LONGITUDE"])
geometry = [Point(xy) for xy in zip(df["LONGITUDE"], df["LATITUDE"])]
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


def process_data(
    data, lat_min=LAT_MIN, lat_max=LAT_MAX, lon_min=LON_MIN, lon_max=LON_MAX
):

    data = data.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

    lat = data.lat.values
    lon = data.lon.values

    val = np.nan_to_num(data.values, nan=0)

    da = xr.DataArray(val, coords={"lat": lat, "lon": lon}, dims=["lat", "lon"])
    da = da.interp(
        lat=np.linspace(lat.min(), lat.max(), 200),
        lon=np.linspace(lon.min(), lon.max(), 200),
    )

    val = gaussian_filter(da.values, sigma=1.2)
    return (da.lon.values, da.lat.values, val)


def save_station_validation_excel(day, wrf, gdf, district_gdf, output_folder):
    date = datetime(YEAR, MONTH, day)

    if date not in gdf.columns:
        print(f"No IMD rainfall column for {date}")
        return
    station_records = []
    # Loop through every AWS station
    for idx, row in gdf.iterrows():
        station = row["STATION"]
        lat = row["LATITUDE"]
        lon = row["LONGITUDE"]
        # IMD rainfall
        imd_rain = pd.to_numeric(row[date], errors="coerce")
        if pd.isna(imd_rain):
            continue
        # WRF rainfall at station
        try:
            if row["STATE"] == "ANDHRA PRADESH":

                print("=" * 60)
                print("Station :", station)
                print("State   :", row["STATE"])
                print("District:", row["DISTRICT"])
                print("Station Lat/Lon:", lat, lon)

                print("WRF Domain")
                print(float(wrf.lat.min()), float(wrf.lat.max()))

                print(float(wrf.lon.min()), float(wrf.lon.max()))

                selected = wrf.sel(lat=lat, lon=lon, method="nearest")

                print(
                    "Nearest grid:",
                    float(selected.lat.values),
                    float(selected.lon.values),
                )

                print("Rainfall:", float(selected.values))

                print("=" * 60)
            wrf_rain = float(wrf.sel(lat=lat, lon=lon, method="nearest").values)
        except:
            wrf_rain = np.nan
        pt = Point(lon, lat)
        district_name = ""
        district_rain = np.nan
        district_match = district_gdf[district_gdf.contains(pt)]
        if not district_match.empty:
            district_name = district_match.iloc[0]["DISTRICT"]
            state_name = district_match.iloc[0]["STATE_UT"]
            station_records.append(
                {
                    "Station Name": station,
                    "State": state_name,
                    "District": district_name,
                    "IMD AWS": imd_rain,
                    "NESAC Forecast": wrf_rain,
                    "NESAC District": district_rain,
                }
            )
        else:
            station_records.append(
                {
                    "Station Name": station,
                    "District": "",
                    "IMD AWS": imd_rain,
                    "NESAC Forecast": wrf_rain,
                    "NESAC District": np.nan,
                }
            )
    df_out = pd.DataFrame(station_records)
    if df_out.empty:
        print("No IMD AWS observations")
        return
    # Save Station Excel
    save_path = os.path.join(
        output_folder, f"Station_Wise_Validation_{YEAR}{MONTH:02d}{day:02d}.xlsx"
    )
    df_out.to_excel(save_path, index=False, engine="openpyxl")
    summary = []
    for district, group in df_out.groupby("District"):
        nstations = len(group)
        imd_avg = group["IMD AWS"].mean()
        imd_max = group["IMD AWS"].max()
        wrf_min = group["NESAC Forecast"].min()
        wrf_max = group["NESAC Forecast"].max()
        nesac_avg = (wrf_min + wrf_max) / 2
        summary.append(
            {
                "State": group["State"].iloc[0],
                "District": district,
                "No of AWS Stations": nstations,
                "IMD AWS Avg (mm)": round(imd_avg, 2),
                "IMD AWS Max (mm)": round(imd_max, 2),
                "NESAC Forecast Range for the District (mm)": f"{wrf_min:.2f}–{wrf_max:.2f}",
                "NESAC Average (mm)": round(nesac_avg, 2),
            }
        )

    summary_df = pd.DataFrame(summary)
    summary_df = summary_df.dropna(subset=["State"])
    summary_path = os.path.join(
        output_folder, f"District_AWS_Summary_{YEAR}{MONTH:02d}{day:02d}.xlsx"
    )
    with pd.ExcelWriter(summary_path, engine="openpyxl") as writer:
        states = sorted(summary_df["State"].astype(str).unique())
        for state in states:
            state_df = summary_df[summary_df["State"] == state].sort_values("District")
            state_df.to_excel(writer, sheet_name=state[:31], index=False)
    print(df_out["State"].value_counts())
    print(f"Saved : {summary_path}")
    print(len(station_records))


print(df.columns)
print(district_gdf.columns)
print(gdf.columns)
