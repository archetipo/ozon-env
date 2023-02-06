from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, \
    AsyncIOMotorCollection
import logging
from pydantic import BaseModel
from pymongo.collection import Collection
from pymongo.typings import _DocumentType

logger = logging.getLogger("asyncio")


class Mongo:
    client: AsyncIOMotorClient = None
    engine: AsyncIOMotorDatabase = None


class DbSettings(BaseModel):
    mongo_user: str
    mongo_pass: str
    mongo_url: str
    mongo_db: str
    mongo_replica: str = ""


db = Mongo()


async def connect_to_mongo(settings: DbSettings):
    logger.info("...")
    mongocfg = f"mongodb://{settings.mongo_user}:{settings.mongo_pass}@{settings.mongo_url}"
    logger.info(f" DB Url {settings.mongo_url} DB {settings.mongo_db}  ..")
    if settings.mongo_replica:
        db.client = AsyncIOMotorClient(
            mongocfg,
            replicaset=settings.mongo_replica,
            connectTimeoutMS=30000, socketTimeoutMS=None,
            minPoolSize=20)
    else:
        db.client = AsyncIOMotorClient(
            mongocfg,
            connectTimeoutMS=30000, socketTimeoutMS=None,
            minPoolSize=20)
        db.engine = db.client[settings.mongo_db]  #
        logging.info("connected new connection")
    return db


async def close_mongo_connection():
    logger.info("colse Db...")
    db.client.close()
    logger.info("closed！")
