from feast import RedisOnlineStore
from feast.infra.offline_stores.contrib.spark_offline_store.spark import SparkOfflineStore

from data.schemas.config import Settings

settings = Settings()

# Offline: S3 Parquet files (read via file path for local dev)
OFFLINE_STORE_PATH = f"s3://{settings.s3_bucket}/features/offline-store"

# Online: Redis
ONLINE_STORE_CONFIG = {
    "type": "redis",
    "connection_string": settings.redis_url,
}
