import pytest
from test_common import *
from ozonenv.core.ModelMaker import ModelMaker, BasicModel
from pydantic.main import ModelMetaclass
from ozonenv.OzonEnv import OzonEnv
from datetime import *
from dateutil.parser import *

pytestmark = pytest.mark.asyncio


@pytestmark
async def test_add_user_static_model():
    path = get_config_path()
    cfg = await OzonEnv.readfilejson(path)
    env = OzonEnv(cfg)
    await env.init_env()
    await env.session_app({"current_session_token": "BA6BA930"})
    user_model = await env.add_static_model('u SEr', User)
    assert user_model.name == "user"
    ret_model = env.get('user')
    assert ret_model.name == "user"
    assert ret_model.static is User
    assert user_model.unique_fields == User.get_unique_fields()
    users = await user_model.find({'uid': 'admin'})
    assert len(users) == 0
    await env.close_db()


@pytestmark
async def test_user_static_model_add_data():
    path = get_config_path()
    cfg = await OzonEnv.readfilejson(path)
    data = await get_user_data()
    env = OzonEnv(cfg)
    await env.init_env()
    env.orm.orm_static_models_map['user'] = User
    await env.session_app({"current_session_token": "BA6BA930"})
    user_model = env.get('user')
    assert user_model.name == "user"
    assert user_model.static == User
    user = await user_model.new(data[0])
    assert user.get('full_name') == "Test Test"
    assert user.get('uid') == "admin"
    await user_model.insert(user)
    users = await user_model.find({'uid': 'admin'})
    assert len(users) == 1
    await env.close_db()


@pytestmark
async def test_add_component_resource_1_product():
    cfg = await OzonEnv.readfilejson(get_config_path())
    schema_dict = await readfilejson(
        "data", "test_resource_1_formio_schema_product.json")
    env = OzonEnv(cfg)
    await env.init_env()
    env.orm.orm_static_models_map['user'] = User
    await env.session_app({"current_session_token": "BA6BA930"})
    product_model = await env.add_schema(schema_dict)
    assert product_model.name == "prodotti"
    # add list prduct and test find/ and distinct
