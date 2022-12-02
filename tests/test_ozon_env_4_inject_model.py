import pytest
from test_common import *
from ozonenv.core.ModelMaker import ModelMaker, BasicModel
from ozonenv.core.BaseModels import CoreModel
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
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    user_model = await env.add_static_model('u SEr', User)
    assert user_model.name == "user"
    ret_model = env.get('user')
    assert ret_model.name == "user"
    assert ret_model.static is User
    assert ['rec_name', 'uid'] == User.get_unique_fields()
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
    env.orm.orm_models.append('user')
    env.orm.orm_static_models_map['user'] = User
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
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
    schema_dict = await readfilejson(
        "data", "test_resource_1_formio_schema_product.json")
    cfg = await OzonEnv.readfilejson(get_config_path())
    env = OzonEnv(cfg)
    await env.init_env()
    await env.orm.add_static_model('user', User)
    assert len(env.orm.orm_models) == 4
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    product_model = await env.add_schema(schema_dict)
    assert product_model.name == "prodotti"
    for i in range(10):
        prod = await product_model.new(
            {"rec_name": f"prod{i}", "label": f"Product{i}"})
        await product_model.insert(prod)
    products = await product_model.find(product_model.get_domain())
    assert len(products) == 10
    assert isinstance(products[3], CoreModel)
    assert products[3].rec_name == "prod3"
    product = await product_model.load({"rec_name": "prod2"})
    assert isinstance(product, CoreModel)
    assert product.label == "Product2"
    # add list prduct and test find/ and distinct
    await env.close_db()


@pytestmark
async def test_add_component_resource_1_product_raw_query():
    cfg = await OzonEnv.readfilejson(get_config_path())
    env = OzonEnv(cfg)
    await env.init_env()
    await env.orm.add_static_model('user', User)
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    product_model = env.get('prodotti')
    products = await product_model.find_raw(product_model.get_domain())
    assert len(products) == 10
    assert isinstance(products[3], dict)
    assert products[3].get('rec_name') == "prod3"
    product = await product_model.load_raw({"rec_name": "prod2"})
    assert isinstance(product, dict)
    assert product.get('label') == "Product2"
    # add list prduct and test find/ and distinct
    await env.close_db()


async def test_aggregation_with_product():
    cfg = await OzonEnv.readfilejson(get_config_path())
    env = OzonEnv(cfg)
    await env.init_env()
    await env.orm.add_static_model('user', User)
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    product_model = env.get('prodotti')
    products = await product_model.find(product_model.get_domain())
    products[3].set('label', 'AProduct3')
    products[3] = await product_model.update(products[3])
    p3 = products[3]
    p2 = products[2]
    assert p3.update_datetime > p2.update_datetime
    res = await product_model.search_all_distinct(
        "rec_name", query=product_model.get_domain(),
        compute_label="rec_name,label", sort="title:asc",
        skip=3, limit=3
    )
    assert len(res) == 3
    assert res[0].title == 'prod3 - AProduct3'
    assert res[1].get('title') == 'prod4 - Product4'
    res = await product_model.search_all_distinct(
        "rec_name", query=product_model.get_domain(),
        sort="title:desc",
        compute_label="label", skip=0, limit=4
    )
    assert len(res) == 4
    assert res[0].rec_name == 'prod9'
    assert res[0].title == 'Product9'
    assert res[3].get('title') == 'Product6'
    await env.close_db()
