import pandas as pd

df = pd.read_excel('Rainfall_Data_April_2026')
station = pd.read_csv('aws_location_cleaned.csv')
print(station.columns)
