import pytest
from test_common import *
from ozonenv.core.ModelMaker import ModelMaker, BasicModel
from pydantic.main import ModelMetaclass
from ozonenv.OzonEnv import OzonEnv
from dateutil.parser import *

pytestmark = pytest.mark.asyncio


@pytestmark
async def test_ozonenv():
    path = get_config_path()
    cfg = await OzonEnv.readfilejson(path)
    env = OzonEnv(cfg)
    assert env.config_system['app_code'] == 'test'


@pytestmark
async def test_init_env():
    path = get_config_path()
    cfg = await OzonEnv.readfilejson(path)
    env = OzonEnv(cfg)
    env.use_cache = False
    await env.init_env()
    await insert_session_collections(env.db)
    session = env.db.engine.get_collection('session')
    stored_obj = await session.find_one({'token': 'BA6BA930'})
    assert stored_obj['uid'] == "admin"
    await env.close_db()


@pytestmark
async def test_make_app_session():
    path = get_config_path()
    cfg = await OzonEnv.readfilejson(path)
    env = OzonEnv(cfg)
    res = await env.make_app_session(
        {"current_session_token": "BA6BA930"},
        redis_url="redis://localhost:10001")
    assert res.fail is False
    assert len(env.models) == 3
    assert env.orm.user_session.get('uid') == "admin"
    assert env.orm.user_session.get('create_datetime') == parse(
        "2022-08-05T05:10:02")
    assert env.orm.user_session.active is True
    assert env.orm.user_session.is_to_delete() is False
    assert env.orm.user_session.is_error() is False


@pytestmark
async def test_make_app_session_error():
    path = get_config_path()
    cfg = await OzonEnv.readfilejson(path)
    env = OzonEnv(cfg)
    res = await env.make_app_session(
        {"current_session_token": "BA6B----"},
        use_cache=True,
        redis_url="redis://localhost:10001")
    assert res.fail is True
    assert res.msg == "Token BA6B---- non abilitato"
