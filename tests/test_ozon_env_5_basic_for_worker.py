import pytest
from test_common import *
from ozonenv.core.ModelMaker import ModelMaker, BasicModel
from pydantic.main import ModelMetaclass
from ozonenv.OzonEnv import OzonWorkerEnv, OzonEnv
from ozonenv.core.OzonOrm import BasicReturn
from datetime import *
from dateutil.parser import *
import traceback

pytestmark = pytest.mark.asyncio


class MockWorker1(OzonWorkerEnv):

    async def session_app(self) -> BasicReturn:
        sres = await super(MockWorker1, self).session_app()
        if sres.fail:
            return self.exception_response(err=res.msg)

        data = await get_file_data()
        self.p_model = await self.add_model(self.params.get("model"))
        self.virtual_doc_model = await self.add_model(
            'virtual_doc', virtual=True)
        self.virtual_row_doc_model = await self.add_model(
            'virtual_row_doc', virtual=True)
        try:
            documento = await self.process_document(data)
            if documento.is_error():
                return self.exception_response(documento.message)

            action_next_page = f"/action/doc/{documento.rec_name}"
            action_next_page = self.next_client_url(
                params=self.params, default_url=action_next_page,
                rec_ref=documento.rec_name)
            result = {
                "done": True,
                "error": False,
                "msg": "",
                "next_action": "redirect",
                "next_page": action_next_page,
                "document_type": self.doc_type,
                "update_data": True,
                "valis": False,
                "model": self.p_model.name,
                "rec_name": documento.rec_name
            }
            res_data = {
                self.topic_name: result,
                self.p_model.name: documento.get_dict_copy()
            }

            return self.success_response(
                msg="Done", data=res_data
            )
        except Exception as e:
            print(f"session_app exception {traceback.format_exc()}")
            return self.exception_response(
                str(e), err_details=str(traceback.format_exc()))

    async def process_document(self, data_doc):
        data_doc['stato'] = ""
        data_doc['document_type'] = ""
        data_doc['document_type'] = ""
        data_doc['ammImpEuro'] = 0.0
        data_doc['ammImpScontatoConIvaEuro'] = 0.0
        data_doc['ammImpScontatoEuro'] = 00
        data_doc['ammIvaEuro'] = 0.0
        data_doc['ammScontoEuro'] = 0.0

        v_doc = await self.virtual_doc_model.new(
            data_doc, rec_name=f"DOC{data_doc['idDg']}")

        if v_doc.is_error():
            return v_doc

        v_doc.selection_value_resources("document_type", "ordine", DOC_TYPES)
        v_doc.set_from_child('ammImpEuro', 'dg15XVoceTe.importo', 0.0)
        v_doc.selction_value("stato", "caricato", "Caricato")

        assert v_doc.ammImpEuro == 1446.16
        assert v_doc.dg18XIndModOrdinat.cdCap == 10133
        for row in v_doc.dg15XVoceCalcolata:
            row_dictr = self.virtual_row_doc_model.get_dict_record(
                row, rec_name=f"{v_doc.rec_name}.{row.nrRiga}")

            row_dictr.set_many({"stato": "", "prova": "test", "prova1": 0})
            row_dictr.selction_value("stato", "caricato", "Caricato")

            assert row_dictr.get('data_value.stato').startswith("Car") is True

            row_o = await self.virtual_row_doc_model.new(
                rec_name=f"{v_doc.rec_name}.{row.nrRiga}",
                data=row_dictr.data.copy()
            )

            assert row_o.nrRiga == row.nrRiga
            assert row_o.rec_name == f"{v_doc.rec_name}.{row.nrRiga}"
            assert row_o.prova == "test"
            assert row_o.data_value.get('stato') == "Caricato"
            assert row_o.get('data_value.stato').startswith("Car") is True
            assert row_o.get('dett.test').startswith("a") is True
            assert row_o.stato == "caricato"
            assert row_o.prova1 == 0

        documento = await self.virtual_doc_model.insert(
            v_doc, force_model=self.p_model)

        return documento


@pytestmark
async def test_base_worker_env():
    path = get_config_path()
    cfg = await OzonWorkerEnv.readfilejson(path)
    worker = OzonWorkerEnv(cfg)
    await worker.init_env()
    worker.params = {
        "current_session_token": "BA6BA930",
        "topic_name": "test_topic",
        "document_type": "standard",
        "model": "",
        "session_is_api": False
    }
    await worker.session_app()
    assert worker.model == ""
    assert worker.topic_name == "test_topic"
    assert worker.doc_type == "standard"
    await worker.close_db()


@pytestmark
async def test_init_schema_for_woker():
    "test_form_2_formio_schema_doc.json"
    schema_list = await get_formio_doc_schema()
    cfg = await OzonEnv.readfilejson(get_config_path())
    env = OzonEnv(cfg)
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    doc_schema = await env.get('component').new(data=schema_list[0])
    doc_schema = await env.get('component').insert(doc_schema)
    assert doc_schema.rec_name == "documento"


@pytestmark
async def test_init_worker_ok():
    cfg = await MockWorker1.readfilejson(get_config_path())
    worker = MockWorker1(cfg)
    res = await worker.make_app_session(
        params={
            "current_session_token": "BA6BA930",
            "topic_name": "test_topic",
            "document_type": "standard",
            "model": "documento",
            "session_is_api": False,
            "action_next_page": {
                "success": {"form": "/open/doc"},
            }
        }
    )
    assert res.fail is False
    assert res.data['test_topic']["error"] is False
    assert res.data['test_topic']["done"] is True
    assert res.data['test_topic']['next_page'] == "/open/doc/DOC99999"
    assert res.data['test_topic']['model'] == "documento"
    assert res.data['documento']['stato'] == "caricato"


@pytestmark
async def test_init_worker_fail():
    cfg = await MockWorker1.readfilejson(get_config_path())
    worker = MockWorker1(cfg)
    res = await worker.make_app_session(
        params={
            "current_session_token": "BA6BA930",
            "topic_name": "test_topic",
            "document_type": "standard",
            "model": "documento",
            "session_is_api": False,
            "action_next_page": {
                "success": {"form": "/open/doc"},
            }
        }
    )
    assert res.fail is True
    assert res.msg == "Errore Duplicato rec_name: DOC99999"
    assert res.data['test_topic']["error"] is True
    assert res.data['test_topic']["done"] is True
    assert res.data['test_topic']['next_page'] == "self"
    assert res.data['test_topic']['model'] == "documento"
