import os
import json
import logging
import time
from dotenv import load_dotenv
from kafka import KafkaProducer
from src.db.connection import engine
import pandas as pd

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FraudProducer:
    def __init__(self):
        self.kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        self.topic = "transactions"
        self.poll_interval = float(os.getenv("KAFKA_POLL_INTERVAL"))
        self.engine = engine
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_servers,
            value_serializer=lambda m: json.dumps(m).encode("utf-8")
        )
        logger.info(f"FraudProducer initialized (topic={self.topic})")

    def fetch_transactions(self) -> pd.DataFrame:
        """ดึงข้อมูล transaction จาก database"""
        query = "SELECT * FROM transactions WHERE id NOT IN (SELECT transaction_id FROM predictions)"
        try:
            df =  pd.read_sql(query, self.engine)
            return [row.to_dict() for _,row in df.iterrows()]
        except Exception as e:
            logger.error(f"Error fetching transactions: {e}")
            return []

    def send_transaction(self, transaction: dict):
        self.producer.send(self.topic, transaction)
        self.producer.flush()
        logger.info(f"Sent transaction id={transaction.get('id')}")

    def run(self):
        logger.info("Starting FraudProducer...")
        while True:
            transactions = self.fetch_transactions()
            if not transactions:
                logger.info("No new transactions to send.")
                time.sleep(self.poll_interval)
                continue
            for txn in transactions:
                self.send_transaction(txn)
            time.sleep(self.poll_interval) 

    def close(self):
        self.producer.close()
        logger.info("Producer closed")

if __name__ == "__main__":
    producer = FraudProducer()
    try:
        producer.run()
    except KeyboardInterrupt:
        producer.close()