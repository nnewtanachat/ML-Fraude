import os
import logging
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.db.connection import engine
from src.db.models import Base

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_PATH = os.getenv("DATA_PATH", str(Path(__file__).resolve().parents[2] / "data" / "fraud.csv"))


def main():
    Base.metadata.create_all(engine)

    df = pd.read_csv(DATA_PATH)
    int_cols = ["num_items", "device_type", "store_type", "is_fraud"]
    bool_cols = ["is_weekend", "is_first_transaction"]

    for col in int_cols:
        df[col] = df[col].astype("Int64")

    for col in bool_cols:
        df[col] = df[col].astype("boolean")

    df.to_sql("transactions", engine, if_exists="append", index=False)

    logger.info("Loaded %d rows into transactions", len(df))


if __name__ == "__main__":
    main()