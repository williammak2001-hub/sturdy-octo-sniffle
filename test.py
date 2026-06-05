import sqlite3
import pandas as pd

conn = sqlite3.connect('racing_platform.db')
# 查詢 2026/06/07 第 1 場的所有馬匹
df = pd.read_sql_query("SELECT * FROM race_results WHERE race_date='2026/06/07' AND race_no=1", conn)
print(df)
conn.close()