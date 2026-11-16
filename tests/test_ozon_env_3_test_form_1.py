import time as time_
from datetime import *

from ozonenv.OzonEnv import OzonEnv
from ozonenv.core.BaseModels import defaultdt, CoreModel
from ozonenv.core.exceptions import SessionException
from test_common import *

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
    data['stato'] = "caricato"
    data['document_type'] = "ordine"
    data['ammImpEuro'] = 0.0
    virtual_doc_model = await env.add_model('virtual_doc', virtual=True)
    assert virtual_doc_model.virtual is True
    assert virtual_doc_model.modelr == virtual_doc_model.mm.instance
    doc = await virtual_doc_model.new(
        data=data,
        rec_name="virtual_data.test",
        data_value={"stato": "Caricato", "document_type": "Ordine"}
    )
    assert doc.get('rec_name') == 'virtual_data.test'
    assert doc.active is True
    assert doc.ammImpEuro == 0.0
    assert doc.dg15XVoceTe.get('importo') == 1446.16
    doc.set_from_child('ammImpEuro', 'dg15XVoceTe.importo', 0.0)
    assert doc.ammImpEuro == 1446.16
    assert doc.idDg == 99999
    assert doc.get('annoRif') == 2022
    assert doc.get('document_type') == 'ordine'
    assert doc.get('stato') == 'caricato'
    assert doc.get('data_value.document_type') == 'Ordine'
    assert doc.dtRegistrazione == '2022-05-23 22:00:00+00:00'
    assert doc.get('dg15XVoceCalcolata.1.imponibile') == 1446.16
    assert doc.to_datetime("dtRegistrazione") == BasicModel.iso_to_utc('2022-05-23 22:00:00+00:00')
    assert doc.dg15XVoceCalcolata[1].get('aliquota') == 20

    doc_not_saved = await virtual_doc_model.insert(doc)
    assert doc_not_saved is None
    assert (
        virtual_doc_model.message
        == "Non è consetito salvare un oggetto virtuale"
    )

    doc_not_saved = await virtual_doc_model.update(doc)
    assert doc_not_saved is None
    assert (
        virtual_doc_model.message
        == "Non e' consentito aggiornare un oggetto virtuale"
    )

    await env.close_db()


@pytestmark
async def test_env_data_file_virtual_model_negative_numbers():
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    data = await get_file_data()
    data['stato'] = "caricato"
    data['document_type'] = "nota_credito"
    data['ammImpEuro'] = -1446.16
    data['saldo'] = "-289.23"
    data['qta'] = "-3"
    data['dg15XVoceTe']['importo'] = "-1446.16"
    data['dg15XVoceCalcolata'][1]['imponibile'] = "-1446.16"
    data['dg15XVoceCalcolata'][1]['aliquota'] = "-20"
    virtual_doc_model = await env.add_model('virtual_doc_neg', virtual=True)
    assert virtual_doc_model.virtual is True
    doc = await virtual_doc_model.new(
        data=data, rec_name="virtual_data.negative"
    )
    assert virtual_doc_model.is_error() is False
    assert doc.get('rec_name') == 'virtual_data.negative'
    assert doc.ammImpEuro == -1446.16
    assert doc.saldo == -289.23
    assert doc.qta == -3
    assert type(doc.qta) is int
    assert doc.dg15XVoceTe.get('importo') == -1446.16
    assert doc.get('dg15XVoceCalcolata.1.imponibile') == -1446.16
    assert doc.dg15XVoceCalcolata[1].get('aliquota') == -20
    # negative index: last row of the list
    assert doc.get('dg15XVoceCalcolata.-1.imponibile') == doc.get(
        f"dg15XVoceCalcolata.{len(doc.dg15XVoceCalcolata) - 1}.imponibile"
    )
    # positive values are untouched
    assert doc.idDg == 99999
    assert doc.get('annoRif') == 2022
    doc.set_from_child('ammImpEuro', 'dg15XVoceTe.importo', 0.0)
    assert doc.ammImpEuro == -1446.16

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
    assert hasattr(component, "content") is False
    assert component.update_datetime == BasicModel.default_datetime()
    assert len(component.get('components')) == 10
    assert (
        env.get('test_form_1').schema.get("components")[0].get("key")
        == "columns"
    )
    await env.close_db()

@pytestmark
async def test_component_test_form_0_1_init_ok():
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    test_form_1_model = env.get('test_form_1')
    # Testa l'inserimento tramite metodo insert
    test_form_1_in = await test_form_1_model.new(
        {
            "rec_name": "first_form2",
            "email": "name2@company.it",
            "firstName": "name 2",
            "lastName": "LastName 2",
            "birthdate": datetime(1987, 12, 20).date(),
            "appointmentDateTime": datetime(2022, 5, 25, 13, 30, 0),
            "howManySeats": 4,
        }
    )
    test_form_1_in.selection_value("favouriteSeason", "autumn", "Autunno")
    test_form_1_in.selection_value("favouriteFood", ["mexican", "chinese"], "Messicano, Cinese")

    test_form_1_in = await test_form_1_model.insert(test_form_1_in)

    assert test_form_1_in.is_error() is False

    assert type(test_form_1_in.get("birthdate")) == datetime
    assert test_form_1_in.get("birthdate") == CoreModel.iso_to_utc(
        "1987-12-20T00:00:00Z"
    )
    assert test_form_1_in.data_value["birthdate"] == "20/12/1987"
    assert type(test_form_1_in.get("appointmentDateTime")) == datetime
    assert test_form_1_in.get("appointmentDateTime") == CoreModel.iso_to_utc(
        "2022-05-25T11:30:00+00:00"
    )
    assert (
        test_form_1_in.data_value["appointmentDateTime"]
        == "25/05/2022 13:30:00"
    )
    assert hasattr(test_form_1_in, "content") is False
    assert test_form_1_in.favouriteSeason == "autumn"
    assert test_form_1_in.data_value["favouriteSeason"] == "Autumn"
    assert test_form_1_in.favouriteFood == ["mexican", "chinese"]
    assert test_form_1_in.data_value["favouriteFood"] == "Mexican, Chinese"
    await env.close_env()

@pytestmark
async def test_component_test_form_1_raw_update():
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    old_test_form_1_model = env.get('test_form_1')
    old_test_form_1 = await old_test_form_1_model.new()
    assert len(old_test_form_1_model.form_fields) == 22
    assert len(old_test_form_1_model.table_columns.keys()) == 7
    assert hasattr(old_test_form_1, "uploadBase64") is False
    assert hasattr(old_test_form_1, "content") is False
    assert hasattr(old_test_form_1, "content1") is True
    data = await readfilejson('data', 'test_form_1.1_formio_schema.json')
    component = await env.get('component').new(data=data)
    assert component.owner_uid == "admin"
    component = await env.get('component').update(component)
    assert component.rec_name == "test_form_1"
    assert not component.update_datetime == BasicModel.default_datetime()
    assert len(component.get('components')) == 11
    data = await readfilejson('data', 'test_form_1.0_formio_schema.json')
    component = await env.get('component').new(data=data)
    await env.get('component').upsert(component)
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
    assert hasattr(old_test_form_1, "content") is False
    assert hasattr(old_test_form_1, "content1") is True
    data_schema = await readfilejson('data', 'test_form_1_formio_schema.json')
    component = await env.insert_update_component(data_schema)
    assert component.owner_uid == "admin"
    assert component.rec_name == "test_form_1"
    assert len(component.get('components')) == 13
    test_form_1_model = env.get('test_form_1')
    test_form_1 = await test_form_1_model.new({})
    assert hasattr(test_form_1, "uploadBase64") is True
    assert hasattr(test_form_1, "content") is True
    assert hasattr(test_form_1, "content1") is True
    # on git workflow time is 2.32 sec.
    assert float(env.get_formatted_metrics(start_time)) < 13.0  # 1.0
    await env.close_env()


@pytestmark
async def test_component_test_form_1_load():
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    component = await env.get('component').load({"rec_name": 'test_form_1'})
    assert component.owner_uid == "admin"
    assert len(component.components) == 13
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
    assert test_form_1_model.model.get_unique_fields() == [
        "rec_name",
        "firstName",
    ]

    test_form_1 = await test_form_1_model.new(data)
    assert test_form_1.is_error() is False
    assert type(test_form_1.birthdate) == datetime
    assert test_form_1.birthdate == CoreModel.iso_to_utc(
        "1987-12-17T00:00:00+00:00"
    )
    assert type(test_form_1.appointmentDateTime1) == datetime
    assert test_form_1.appointmentDateTime1 == CoreModel.iso_to_utc(defaultdt)
    dictres = test_form_1.model_dump()
    assert dictres['appointmentDateTime1'] == CoreModel.iso_to_utc(defaultdt)
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
    assert test_form_1.get('birthdate') == test_form_1_model.dte.parse_to_utc_datetime("1987-12-17T00:00:00+00:00")

    assert test_form_1.get('data_value.birthdate') == "17/12/1987"
    test_form_1_us = await test_form_1_model.insert(test_form_1)
    assert test_form_1_us.is_error() is False
    assert test_form_1_us.get('appointmentDateTime') == BasicModel.iso_to_utc(
        '2022-05-25T11:30:00+00:00'
    )
    assert test_form_1_us.data_value.get('appointmentDateTime') == "25/05/2022 13:30:00"
    assert test_form_1_us.get("owner_uid") == test_form_1_model.user_session.get(
        'uid'
    )
    assert test_form_1_us.get("rec_name") == "first_form"
    assert test_form_1_us.create_datetime.date() == test_form_1_us.utc_now().date()
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
    assert (
        test_form_1_model.message == "Duplicate key error"
        " rec_name: first_form"
    )

    await env.set_lang("it")

    test_form_1.set('rec_name', "first form")
    test_form_e1 = await test_form_1_model.insert(test_form_1)
    assert test_form_e1 is None
    assert (
        test_form_1_model.message == "Caratteri non consetiti"
        " nel campo name: first form"
    )

    data_err = data.copy()
    data_err['rec_name'] = "first/form"
    test_form_e2 = await test_form_1_model.new(data=data_err)
    assert test_form_e2 is None
    assert (
        test_form_1_model.message == "Caratteri non consetiti "
        "nel campo name: first/form"
    )

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
    assert test_form_1_copy.create_datetime.date() == datetime.utcnow().date()
    test_form_1_copy = await test_form_1_model.insert(test_form_1_copy)
    assert test_form_1_copy.is_error() is False
    # test rec_name --> model.ids
    await env.close_env()


async def test_test_form_1_update_record():
    data = await readfilejson('data', 'test_form_1_formio_data.json')
    env = OzonEnv()
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    test_form_1_model = await env.add_model('test_form_1')
    data['birthdate'] = '1987-12-18T12:00:00+02:00'
    test_form_1_upd = await test_form_1_model.upsert(data)
    assert test_form_1_upd.is_error() is False
    assert test_form_1_upd.get('birthdate') == BasicModel.iso_to_utc('1987-12-18T00:00:00+00:00')
    assert test_form_1_upd.get('appointmentDateTime') == BasicModel.iso_to_utc(
        '2022-05-25T11:30:00+00:00'
    )
    assert test_form_1_upd.get('data_value.appointmentDateTime') == "25/05/2022 13:30:00"
    assert test_form_1_upd.get('data_value.birthdate') == "18/12/1987"
    assert test_form_1_upd.get('data_value.favouriteFood') == "Mexican, Chinese"

    # Aggiorna la data con un oggetto datetime.date
    test_form_1_upd.birthdate = CoreModel.iso_to_utc("1987-12-18T00:00:00Z").date()
    test_form_1_upd.dataGrid = [{
        "textField": "abc123",
        "birthdateDg": "1990-12-31",
        "appointmentDateTimeDg": "2000-01-01 21:00:00",
        "checkbox": False,
        "favouriteSeasonDg": "autumn"
    }]
    test_form_1_upd.dataGrid2 = [{
        "textField": "zyx",
        "birthdateDg": "2000-01-01T00:00:00Z",
        "appointmentDateTimeDg": "2000-12-31T00:00:00+01:00",
        "checkbox": False
    }]
    test_form_1_upd = await test_form_1_model.update(test_form_1_upd)

    assert type(test_form_1_upd.birthdate) == datetime
    assert test_form_1_upd.birthdate == CoreModel.iso_to_utc("1987-12-18T00:00:00Z")
    assert test_form_1_upd.data_value.get("birthdate") == "18/12/1987"
    assert len(test_form_1_upd.dataGrid) == 1
    assert test_form_1_upd.dataGrid[0].birthdateDg == CoreModel.iso_to_utc("1990-12-31T00:00:00Z")
    assert test_form_1_upd.dataGrid[0].appointmentDateTimeDg == CoreModel.iso_to_utc("2000-01-01T21:00:00+01:00")
    assert test_form_1_upd.dataGrid[0].favouriteSeasonDg == "autumn"
    assert test_form_1_upd.dataGrid[0].data_value != {}
    assert test_form_1_upd.dataGrid[0].data_value["birthdateDg"] == "31/12/1990"
    assert test_form_1_upd.dataGrid[0].data_value["appointmentDateTimeDg"] == "01/01/2000 21:00:00"
    assert test_form_1_upd.dataGrid[0].data_value["favouriteSeasonDg"] == "Autumn"
    assert len(test_form_1_upd.dataGrid2) == 1
    assert test_form_1_upd.dataGrid2[0].birthdateDg == CoreModel.iso_to_utc("2000-01-01T00:00:00Z")
    assert test_form_1_upd.dataGrid2[0].appointmentDateTimeDg == CoreModel.iso_to_utc("2000-12-31T00:00:00+01:00")
    assert test_form_1_upd.dataGrid2[0].data_value != {}
    assert test_form_1_upd.dataGrid2[0].data_value["birthdateDg"] == "01/01/2000"
    assert test_form_1_upd.dataGrid2[0].data_value["appointmentDateTimeDg"] == "31/12/2000 00:00:00"


    await env.close_env()
