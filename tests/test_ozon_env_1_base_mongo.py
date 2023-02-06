import pytest
from test_common import *
from ozonenv.core.ModelMaker import ModelMaker, BasicModel
from pydantic.main import ModelMetaclass
from ozonenv.OzonEnv import OzonEnv
from dateutil.parser import *
from ozonenv.core.db.mongodb_utils import (
    connect_to_mongo,
    close_mongo_connection,
    DbSettings,
    Mongo,
    AsyncIOMotorClient,
    AsyncIOMotorCollection
)

pytestmark = pytest.mark.asyncio


@pytestmark
async def test_ozonenv_cfg():
    init_env_var()
    config_system = {
        "app_code": os.getenv("APP_CODE"),
        "mongo_user": os.getenv("MONGO_USER"),
        "mongo_pass": os.getenv("MONGO_PASS"),
        "mongo_url": os.getenv("MONGO_URL"),
        "mongo_db": os.getenv("MONGO_DB"),
        "mongo_replica": os.getenv("MONGO_REPLICA"),
        "models_folder": os.getenv("MODELS_FOLDER")
    }
    env = OzonEnv(config_system)
    assert env.config_system['app_code'] == 'test'
    assert env.config_system['app_code'] == 'test'


@pytestmark
async def test_ozonenv_from_os_env():
    env = OzonEnv()
    assert env.config_system['app_code'] == 'test'


async def test_init_env_db_exist():
    config_system = {
        "app_code": os.getenv("APP_CODE"),
        "mongo_user": os.getenv("MONGO_USER"),
        "mongo_pass": os.getenv("MONGO_PASS"),
        "mongo_url": os.getenv("MONGO_URL"),
        "mongo_db": os.getenv("MONGO_DB"),
        "mongo_replica": os.getenv("MONGO_REPLICA")
    }
    db_settings = DbSettings(**config_system)
    db = await connect_to_mongo(db_settings)
    env = OzonEnv()
    await env.init_env(db=db)
    session = env.db.engine.get_collection('session')
    assert isinstance(session, AsyncIOMotorCollection)
    await env.close_env()
    assert db.client.is_primary
    await close_mongo_connection()
    with pytest.raises(Exception) as excinfo:
        assert db.client.is_primary
    assert str(excinfo.value) == 'Cannot use MongoClient after close'


@pytestmark
async def test_init_env():
    # init_env_var()
    # path = get_config_path()
    # app_setting = await OzonEnv.readfilejson(path)
    env = OzonEnv()
    env.use_cache = False
    await env.init_env()
    await init_main_collections(env.db)
    session = env.db.engine.get_collection('session')
    stored_obj = await session.find_one({'token': 'BA6BA930'})
    assert stored_obj['uid'] == "admin"
    settings = env.db.engine.get_collection('settings')
    query = {"rec_name":
                 env.config_system.get("app_code")}
    set_stored_obj = await settings.find_one(query)
    assert set_stored_obj['rec_name'] == "test"
    await env.close_db()


@pytestmark
async def test_make_app_session():
    env = OzonEnv()
    res = await env.make_app_session(
        {"current_session_token": "BA6BA930"},
        redis_url="redis://localhost:10001")
    assert res.fail is False
    assert len(env.models) == 4
    assert env.orm.user_session.get('uid') == "admin"
    assert env.orm.user_session.get('create_datetime') == parse(
        "2022-08-05T05:10:02")
    assert env.orm.user_session.active is True
    assert env.orm.user_session.is_to_delete() is False
    assert env.orm.user_session.is_error() is False


@pytestmark
async def test_make_app_session_error():
    env = OzonEnv()
    res = await env.make_app_session(
        {"current_session_token": "BA6B----"},
        use_cache=True,
        redis_url="redis://localhost:10001")
    assert res.fail is True
    assert res.msg == "Token BA6B---- non abilitato"
