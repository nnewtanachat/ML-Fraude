import os
import json
import logging
import time

import pandas as pd
from dotenv import load_dotenv
from kafka import KafkaProducer
from kafka.errors import KafkaError

from src.db.connection import engine

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FraudProducer:
    def __init__(self):
        self.kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        self.topic = "transactions"
        self.poll_interval = float(os.getenv("KAFKA_POLL_INTERVAL", "10"))
        self.engine = engine
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_servers,
            value_serializer=lambda m: json.dumps(m, default=str).encode("utf-8"),
            retries=3,
            acks="all",              # รอ broker confirm ก่อนถือว่าส่งสำเร็จ
            linger_ms=100,           # batch messages 100ms ก่อนส่ง (เร็วขึ้น)
            batch_size=16384,
        )
        logger.info("FraudProducer initialized (topic=%s, servers=%s)", self.topic, self.kafka_servers)

    def fetch_transactions(self) -> list[dict]:
        """ดึง transactions ที่ยังไม่ถูก predict."""
        query = """
            SELECT * FROM transactions
            WHERE id NOT IN (SELECT transaction_id FROM predictions)
        """
        try:
            df = pd.read_sql(query, self.engine)
            return [row.to_dict() for _, row in df.iterrows()]
        except Exception as e:
            logger.error("Error fetching transactions: %s", e)
            return []

    def send_transaction(self, transaction: dict) -> None:
        """Send single transaction to Kafka with error callback."""
        future = self.producer.send(self.topic, transaction)
        future.add_errback(self._on_send_error, txn_id=transaction.get("id"))

    def _on_send_error(self, exc: KafkaError, txn_id=None) -> None:
        logger.error("Failed to send transaction id=%s: %s", txn_id, exc)

    def run(self) -> None:
        logger.info("Starting FraudProducer...")
        while True:
            transactions = self.fetch_transactions()
            if not transactions:
                logger.info("No new transactions to send.")
                time.sleep(self.poll_interval)
                continue

            for txn in transactions:
                self.send_transaction(txn)

            # Batch flush — flush ทีเดียวหลังส่งทั้ง batch (เร็วกว่า flush ทุก message)
            self.producer.flush()
            logger.info("Sent %d transactions", len(transactions))
            time.sleep(self.poll_interval)

    def close(self) -> None:
        self.producer.flush()
        self.producer.close()
        logger.info("Producer closed")


if __name__ == "__main__":
    producer = FraudProducer()
    try:
        producer.run()
    except KeyboardInterrupt:
        producer.close()
