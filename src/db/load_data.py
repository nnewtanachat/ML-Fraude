import pandas as pd
from connection import engine
from models import Base

Base.metadata.create_all(engine)

df = pd.read_csv("../../data/fraud.csv")
int_cols = ["num_items", "device_type", "store_type", "is_fraud"]
bool_cols = ["is_weekend", "is_first_transaction"]

for col in int_cols:
    df[col] = df[col].astype("Int64")

for col in bool_cols:
    df[col] = df[col].astype("boolean")

df.to_sql("transactions", engine, if_exists="append", index=False)

print(f"Loaded {len(df)} rows into transactions")