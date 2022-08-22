import pytest
from test_common import *
from ozonenv.core.ModelMaker import ModelMaker, BasicModel
from pydantic.main import ModelMetaclass
from ozonenv.OzonEnv import OzonEnv
from datetime import *
from dateutil.parser import *

pytestmark = pytest.mark.asyncio


@pytestmark
async def test_component_test_form_1_init():
    path = get_config_path()
    cfg = await OzonEnv.readfilejson(path)
    env = OzonEnv(cfg)
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    data = await readfilejson('data', 'test_form_1_formio_schema.json')

    component = await env.get('component').new(data=data)
    assert component.owner_uid == "admin"
    component = await env.get('component').insert(component)
    assert component.rec_name == "test_form_1"
    assert len(component.get('components')) == 12
    await env.close_db()


@pytestmark
async def test_env_data_file_virtual_model():
    path = get_config_path()
    cfg = await OzonEnv.readfilejson(path)
    env = OzonEnv(cfg)
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    data = await get_file_data()
    data['stato'] = ""
    data['document_type'] = ""
    data['ammImpEuro'] = 0.0
    virtual_doc_model = await env.add_model('virtual_doc', virtual=True)
    assert virtual_doc_model.virtual is True
    assert virtual_doc_model.model_record == virtual_doc_model.mm.instance
    doc = await virtual_doc_model.new(data=data, rec_name="virtual_data.test")
    assert doc.get('rec_name') == 'virtual_data.test'
    assert doc.active is True
    doc.selction_value("stato", "caricato", "Caricato")
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
async def test_component_test_form_1_load():
    path = get_config_path()
    cfg = await OzonEnv.readfilejson(path)
    env = OzonEnv(cfg)
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    component = await env.get('component').load({"rec_name": 'test_form_1'})
    assert component.owner_uid == "admin"
    assert len(component.components) == 12
    assert component.get(f'components.{3}.label') == "Panel"
    await env.close_db()


@pytestmark
async def test_test_form_1_init_data():
    path = get_config_path()
    cfg = await OzonEnv.readfilejson(path)
    data = await readfilejson('data', 'test_form_1_formio_data.json')
    env = OzonEnv(cfg)
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    test_form_1_model = await env.add_model('test_form_1')
    assert test_form_1_model.unique_fields == ["rec_name", "firstName"]
    test_form_1 = await test_form_1_model.new(data=data)
    assert test_form_1.is_error() is False
    assert test_form_1.get('birthdate') == parse("1987-12-17T12:00:00")
    await env.close_db()


@pytestmark
async def test_test_form_1_insert_ok():
    path = get_config_path()
    cfg = await OzonEnv.readfilejson(path)
    data = await readfilejson('data', 'test_form_1_formio_data.json')
    env = OzonEnv(cfg)
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    test_form_1_model = await env.add_model('test_form_1')
    test_form_1 = await test_form_1_model.new(data=data)

    assert test_form_1.is_error() is False
    assert test_form_1.get("owner_uid") == ""
    assert test_form_1.get("rec_name") == "first_form"
    assert test_form_1.get('birthdate') == parse("1987-12-17T12:00:00")
    assert test_form_1.get('data_value.birthdate') == "17/12/1987 12:00:00"

    test_form_1 = await test_form_1_model.insert(test_form_1)
    assert test_form_1.is_error() is False
    assert test_form_1.get("owner_uid") == test_form_1_model.user_session.get(
        'uid')
    assert test_form_1.get("rec_name") == "first_form"
    assert test_form_1.create_datetime.date() == datetime.now().date()
    await env.close_db()


@pytestmark
async def test_test_form_1_insert_ko():
    path = get_config_path()
    cfg = await OzonEnv.readfilejson(path)
    data = await readfilejson('data', 'test_form_1_formio_data.json')
    env = OzonEnv(cfg)
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    test_form_1_model = await env.add_model('test_form_1')
    test_form_1 = await test_form_1_model.new(data=data)
    test_form_1_new = await test_form_1_model.insert(test_form_1)
    assert test_form_1_new is None
    assert test_form_1_model.message == "Errore Duplicato rec_name: first_form"

    await env.set_lang("en")
    test_form_en = await test_form_1_model.insert(test_form_1)
    assert test_form_en is None
    assert test_form_1_model.message == "Duplicate key error rec_name: first_form"

    await env.set_lang("it")

    test_form_1.set('rec_name', "first form")
    test_form_e1 = await test_form_1_model.insert(test_form_1)
    assert test_form_e1 is None
    assert test_form_1_model.message == "Caratteri non consetiti nel campo name: first form"

    data_err = data.copy()
    data_err['rec_name'] = "first/form"
    test_form_e2 = await test_form_1_model.new(data=data_err)
    assert test_form_e2 is None
    assert test_form_1_model.message == "Caratteri non consetiti nel campo name: first/form"

    await env.close_db()


@pytestmark
async def test_test_form_1_copy_record():
    path = get_config_path()
    cfg = await OzonEnv.readfilejson(path)
    env = OzonEnv(cfg)
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
    await env.close_db()
