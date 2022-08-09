import pytest
from test_common import *
from ozonenv.core.ModelMaker import ModelMaker, BasicModel
from pydantic.main import ModelMetaclass
from ozonenv.core.OzonRecord import Record

# from ozonenv.core.i18n import i18nlocaledir

pytestmark = pytest.mark.asyncio


@pytestmark
async def test_make_form_data():
    data_json = await get_file_data()
    test_1 = ModelMaker("test_base")
    test_1.from_data_dict(data_json)
    test_1.new()
    assert test_1.model_name == "test_base"
    assert isinstance(test_1.instance, BasicModel) is True
    assert test_1.instance.annoRif == 2022
    assert test_1.instance.dg11XContr.flRate is True
    assert len(test_1.instance.dg15XVoceCalcolata) == 4
    assert test_1.instance.dg15XVoceCalcolata[1].importo == 289.23
    rec = Record(
        model="doc_test", rec_name="test",
        data=test_1.instance.get_dict_copy())
    assert rec.get('dg15XVoceTe.importo') == 1446.16
    assert rec.get('dg15XVoceCalcolata.1.importo') == 289.23


@pytestmark
async def test_make_form_schema():
    schema = await get_formio_schema()
    formio_data_json = await get_formio_data()
    test_2 = ModelMaker("component")
    test_2.from_formio(schema)
    assert test_2.model_name == "component"
    assert isinstance(test_2.model, ModelMetaclass) is True
    assert test_2.unique_fields == ["rec_name", "firstName"]
    assert test_2.required_fields == ["rec_name", "firstName"]
    assert test_2.components_logic == []
    assert "rec_name" in list(test_2.no_clone_field_keys.keys())
    test_2.new()
    assert isinstance(test_2.instance, BasicModel) is True
    test_2.new(formio_data_json)
    assert test_2.instance.textFieldTab1 == "text in tab 1"
    assert test_2.instance.email == 'name@company.it'
    assert len(test_2.instance.dataGrid) == 2
    assert test_2.instance.dataGrid[0].textField == 'abc'
    assert test_2.instance.dataGrid[1].textField == 'def'
    assert test_2.instance.survey[
               'howWouldYouRateTheFormIoPlatform'] == 'excellent'


@pytestmark
async def test_make_form_cond_schema():
    schema = await get_formio_schema_conditional()
    formio_data_json = await get_formio_schema_conditional_data_hide()
    test_2 = ModelMaker("component")
    test_2.from_formio(schema)
    assert test_2.model_name == "component"
    test_2.new(formio_data_json)
    assert test_2.instance.username == "wrong"
    assert test_2.realted_fields_logic == {'username': ['secret'],
                                           'password': ['secret']}
    d = test_2.instance.get_dict()
    assert d == {'id': d.get('id'), 'app_code': [], 'parent': '',
                 'process_id': '',
                 'process_task_id': '', 'data_value': {}, 'owner_name': '',
                 'deleted': 0, 'list_order': 0,
                 'owner_uid': '', 'owner_mail': '', 'owner_function': '',
                 'owner_function_type': '', 'owner_sector': '',
                 'owner_sector_id': 0, 'owner_personal_type': '',
                 'owner_job_title': '', 'update_uid': '', 'sys': False,
                 'default': False, 'active': True, 'demo': False, 'childs': [],
                 'create_datetime': '1970-01-01T00:00:00',
                 'update_datetime': '1970-01-01T00:00:00', 'rec_name': '',
                 'username': 'wrong', 'password': 'incorrect', 'secret': ''}
