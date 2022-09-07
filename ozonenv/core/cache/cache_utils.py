import aioredis
import logging
from .cache import ioredis, get_redis, RedisBackend

logger = logging.getLogger(__name__)


async def init_cache(url="redis://redis_cache"):
    logger.info("...")
    logger.info(f" start Redis Cache ..")
    ioredis.client = aioredis.from_url(
        url, encoding="utf8", decode_responses=False,
        socket_keepalive=True,
    )
    ioredis.cache = RedisBackend(ioredis.client)
    logging.info("new Redis Cache created")


async def stop_cache():
    logger.info("stopping Redis Cache...")
    redis = await get_redis()
    await redis.close()
    logger.info("stopped！")
