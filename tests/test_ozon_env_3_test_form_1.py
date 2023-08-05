import time as time_
from datetime import *

from dateutil.parser import *

from ozonenv.OzonEnv import OzonEnv
from ozonenv.core.exceptions import SessionException
from test_common import *
import iso8601
pytestmark = pytest.mark.asyncio


@pytestmark
async def test_env_orm_basic():
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    executed_cmd = await env.orm.runcmd("ls -alh")
    await env.orm.set_lang()
    assert env.models['component'].model.str_name() == 'component'
    assert executed_cmd is None
    await env.close_db()


@pytestmark
async def test_env_data_file_virtual_model():
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    data = await get_file_data()
    data['stato'] = ""
    data['document_type'] = ""
    data['ammImpEuro'] = 0.0
    virtual_doc_model = await env.add_model('virtual_doc', virtual=True)
    assert virtual_doc_model.virtual is True
    assert virtual_doc_model.modelr == virtual_doc_model.mm.instance
    doc = await virtual_doc_model.new(data=data, rec_name="virtual_data.test")
    assert doc.get('rec_name') == 'virtual_data.test'
    assert doc.active is True
    doc.selection_value("stato", "caricato", "Caricato")
    doc.selection_value_resources("document_type", "ordine", DOC_TYPES)
    doc.set_from_child('ammImpEuro', 'dg10XComm.ammImpEuro', 0.0)
    assert doc.ammImpEuro == 0.0
    assert doc.dg15XVoceTe.get('importo') == 1446.16
    doc.set_from_child('ammImpEuro', 'dg15XVoceTe.importo', 0.0)
    assert doc.ammImpEuro == 1446.16
    assert doc.idDg == 99999
    assert doc.get('annoRif') == 2022
    assert doc.get('document_type') == 'ordine'
    assert doc.get('stato') == 'caricato'
    assert doc.get('data_value.document_type') == 'Ordine'
    assert doc.dtRegistrazione == '2022-05-24T00:00:00'
    assert doc.get('dg15XVoceCalcolata.1.imponibile') == 1446.16
    assert doc.to_datetime('dtRegistrazione') == parse('2022-05-24T00:00:00')
    assert doc.dg15XVoceCalcolata[1].get('aliquota') == 20

    doc_not_saved = await virtual_doc_model.insert(doc)
    assert doc_not_saved is None
    assert (
            virtual_doc_model.message ==
            "Non è consetito salvare un oggetto virtuale"
    )

    doc_not_saved = await virtual_doc_model.update(doc)
    assert doc_not_saved is None
    assert (
            virtual_doc_model.message ==
            "Non e' consentito aggiornare un oggetto virtuale"
    )

    await env.close_db()


@pytestmark
async def test_component_test_form_1_init():
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    data = await readfilejson('data', 'test_form_1.0_formio_schema.json')
    component = await env.insert_update_component(data)
    assert component.owner_uid == "admin"
    assert component.rec_name == "test_form_1"
    assert component.update_datetime == parse("1970-01-01T00:00:00")
    assert len(component.get('components')) == 10
    assert (
            env.get('test_form_1').schema.get(
                "components")[0].get("key") == "columns"
    )
    await env.close_db()


@pytestmark
async def test_component_test_form_1_raw_update():
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    old_test_form_1_model = env.get('test_form_1')
    old_test_form_1 = await old_test_form_1_model.new()
    assert hasattr(old_test_form_1, "uploadBase64") is False
    assert hasattr(old_test_form_1, "content") is False
    assert hasattr(old_test_form_1, "content1") is True
    data = await readfilejson('data', 'test_form_1.1_formio_schema.json')
    component = await env.get('component').new(data=data)
    assert component.owner_uid == "admin"
    component = await env.get('component').update(component)
    assert component.rec_name == "test_form_1"
    assert not component.update_datetime == parse("1970-01-01T00:00:00")
    assert len(component.get('components')) == 11
    await env.close_env()


@pytestmark
async def test_component_test_form_1_update():
    start_time = time_.monotonic()
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    old_test_form_1_model = env.get('test_form_1')
    old_test_form_1 = await old_test_form_1_model.new()
    assert hasattr(old_test_form_1, "uploadBase64") is False
    assert hasattr(old_test_form_1, "content") is True
    assert hasattr(old_test_form_1, "content1") is True
    data_schema = await readfilejson('data', 'test_form_1_formio_schema.json')
    component = await env.insert_update_component(data_schema)
    assert component.owner_uid == "admin"
    assert component.rec_name == "test_form_1"
    assert len(component.get('components')) == 12
    test_form_1_model = env.get('test_form_1')
    test_form_1 = await test_form_1_model.new({})
    assert hasattr(test_form_1, "uploadBase64") is True
    assert hasattr(test_form_1, "content") is True
    assert hasattr(test_form_1, "content1") is True
    # on git workflow time is 2.32 sec.
    assert float(env.get_formatted_metrics(start_time)) < 3.0  # 1.0
    await env.close_env()


@pytestmark
async def test_component_test_form_1_load():
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    component = await env.get('component').load({"rec_name": 'test_form_1'})
    assert component.owner_uid == "admin"
    assert len(component.components) == 12
    assert component.get(f'components.{3}.label') == "Panel"
    await env.close_env()


@pytestmark
async def test_test_form_1_public_init_data_err():
    data = await readfilejson('data', 'test_form_1_formio_data.json')
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "PUBLIC"}
    await env.session_app()
    # model is in env.models
    assert env.user_session.uid == "public"
    assert env.user_session.is_public is True
    assert env.orm.user_session.is_public is True
    settings = env.get('settings')
    with pytest.raises(SessionException) as excinfo:
        await settings.find({})
    assert 'Permission Denied' in str(excinfo)
    await env.close_env()


@pytestmark
async def test_test_form_1_init_data():
    path = get_config_path()
    data = await readfilejson('data', 'test_form_1_formio_data.json')
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    # model is in env.models

    test_form_1_model = env.get('test_form_1')
    assert test_form_1_model.model.get_unique_fields() == ["rec_name",
                                                           "firstName"]

    test_form_1 = await test_form_1_model.new(data)
    assert test_form_1.is_error() is False
    assert test_form_1.birthdate == iso8601.parse_date("1987-12-17T12:00:00+02:00")
    await env.close_env()


@pytestmark
async def test_test_form_1_insert_ok():
    path = get_config_path()
    data = await readfilejson('data', 'test_form_1_formio_data.json')
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    # model exist in env models
    assert 'test_form_1' in list(env.models.keys())
    test_form_1_model = env.get('test_form_1')
    test_form_1 = await test_form_1_model.new(data=data)

    assert test_form_1.is_error() is False
    assert test_form_1.get("owner_uid") == ""
    assert test_form_1.get("rec_name") == "first_form"
    assert test_form_1.get('birthdate') == iso8601.parse_date("1987-12-17T12:00:00+02:00")
    assert test_form_1.get('data_value.birthdate') == "17/12/1987"

    test_form_1 = await test_form_1_model.insert(test_form_1)
    assert test_form_1.is_error() is False
    assert test_form_1.get("owner_uid") == test_form_1_model.user_session.get(
        'uid')
    assert test_form_1.get("rec_name") == "first_form"
    assert test_form_1.create_datetime.date() == datetime.now().date()
    await env.close_env()





@pytestmark
async def test_test_form_1_insert_ko():
    data = await readfilejson('data', 'test_form_1_formio_data.json')
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    # model is in env.models
    assert 'test_form_1' in list(env.models.keys())
    test_form_1_model = env.get('test_form_1')
    test_form_1 = await test_form_1_model.new(data=data)
    test_form_1_new = await test_form_1_model.insert(test_form_1)
    assert test_form_1_new is None
    assert test_form_1_model.message == "Errore Duplicato rec_name: first_form"

    await env.set_lang("en")
    test_form_en = await test_form_1_model.insert(test_form_1)
    assert test_form_en is None
    assert test_form_1_model.message == "Duplicate key error" \
                                        " rec_name: first_form"

    await env.set_lang("it")

    test_form_1.set('rec_name', "first form")
    test_form_e1 = await test_form_1_model.insert(test_form_1)
    assert test_form_e1 is None
    assert test_form_1_model.message == "Caratteri non consetiti" \
                                        " nel campo name: first form"

    data_err = data.copy()
    data_err['rec_name'] = "first/form"
    test_form_e2 = await test_form_1_model.new(data=data_err)
    assert test_form_e2 is None
    assert test_form_1_model.message == "Caratteri non consetiti " \
                                        "nel campo name: first/form"

    await env.close_env()


@pytestmark
async def test_test_form_1_copy_record():
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    test_form_1_model = await env.add_model('test_form_1')
    test_form_1_copy = await test_form_1_model.copy({'rec_name': 'first_form'})
    assert test_form_1_copy.get("rec_name") == f"first_form_copy"
    assert test_form_1_copy.get("owner_uid") == env.user_session.get('uid')
    assert test_form_1_copy.create_datetime.date() == datetime.now().date()
    test_form_1_copy = await test_form_1_model.insert(test_form_1_copy)
    assert test_form_1_copy.is_error() is False
    # test rec_name --> model.ids
    await env.close_env()
