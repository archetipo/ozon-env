import pytest
from test_common import *
from ozonenv.core.ModelMaker import ModelMaker, BasicModel
from ozonenv.core.BaseModels import CoreModel
from pydantic.main import ModelMetaclass
from ozonenv.OzonEnv import OzonWorkerEnv, OzonEnv, BasicReturn
from datetime import *
from dateutil.parser import *
import traceback
import locale

pytestmark = pytest.mark.asyncio


class MockWorker1(OzonWorkerEnv):

    async def session_app(self) -> BasicReturn:
        sres = await super(MockWorker1, self).session_app()
        if sres.fail:
            return self.exception_response(err=res.msg)

        data = await get_file_data()
        self.p_model = await self.add_model(self.params.get("model"))
        self.row_model = await self.add_model("riga_doc")
        assert self.p_model.name == "documento_beni_servizi"
        assert self.p_model.data_model == "documento"

        self.virtual_doc_model = await self.add_model(
            'virtual_doc', virtual=True,
            data_model="documento_beni_servizi")

        self.virtual_row_doc_model = await self.add_model(
            'virtual_row_doc', virtual=True,
            data_model='riga_doc')
        try:
            documento = await self.process_document(data)
            if not documento:
                return self.exception_response(
                    self.virtual_row_doc_model.message)

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
                self.p_model.name: documento.get_dict_json()
            }

            return self.success_response(
                msg="Done", data=res_data
            )
        except Exception as e:
            print(f"session_app exception {traceback.format_exc()}")
            return self.exception_response(
                str(e), err_details=str(traceback.format_exc()))

    async def process_document(self, data_doc) -> CoreModel:
        data_doc['stato'] = ""
        data_doc['tipologia'] = []
        data_doc['document_type'] = ""
        data_doc['document_type'] = ""
        data_doc['ammImpEuro'] = 0.0
        data_doc['ammImpScontatoConIvaEuro'] = 0.0
        data_doc['ammImpScontatoEuro'] = 00
        data_doc['ammIvaEuro'] = 0.0
        data_doc['ammScontoEuro'] = 0.0
        data_doc['anomalia_gestita'] = False

        v_doc = await self.virtual_doc_model.new(
            data_doc,
            rec_name=f"DOC{data_doc['idDg']}",
            trnf_config={
                "dtRegistrazione": {"type": 'date'},
                "ammImpEuro": {"type": 'float', "dp": 2},
            })

        if self.virtual_doc_model.is_error():
            return v_doc

        v_doc.selection_value_resources("document_type", "ordine", DOC_TYPES)
        v_doc.selection_value('tipologia', ["a", "b"],
                              ["A", "B"])
        v_doc.set_from_child('ammImpEuro', 'dg15XVoceTe.importo', 0.0)
        v_doc.selection_value("stato", "caricato", "Caricato")

        assert v_doc.ammImpEuro == 1446.16
        assert v_doc.dg18XIndModOrdinat.cdCap == 10133
        assert v_doc.dg18XIndModOrdinat.denominazione == "Mario Rossi"

        for id, row in enumerate(v_doc.dg15XVoceCalcolata):
            row_dictr = self.virtual_row_doc_model.get_dict_record(
                row, rec_name=f"{v_doc.rec_name}.{row.nrRiga}")

            row_dictr.set_many({"stato": "", "prova": "test", "prova1": 0})
            row_dictr.selection_value("stato", "caricato", "Caricato")
            row_dictr.selection_value(
                'tipologia', ["a", "b"], ["A", "B"])

            assert row_dictr.get('data_value.stato').startswith("Car") is True

            row_o = await self.virtual_row_doc_model.new(
                rec_name=f"{v_doc.rec_name}.{row.nrRiga}",
                data=row_dictr.data.copy()
            )

            assert row_o.nrRiga == row.nrRiga
            assert row_o.rec_name == f"{v_doc.rec_name}.{row.nrRiga}"
            assert row_o.prova == "test"
            assert row_o.tipologia == ["a", "b"]
            assert row_o.data_value.get('stato') == "Caricato"
            assert row_o.get('data_value.stato').startswith("Car") is True
            assert row_o.get('dett.test').startswith("a") is True
            assert row_o.stato == "caricato"
            assert row_o.prova1 == 0

            row_db = await self.virtual_row_doc_model.insert(row_o)

            if not row_db:
                return row_db

            assert row_db.nrRiga == row.nrRiga
            assert row_db.rec_name == f"{v_doc.rec_name}.{row.nrRiga}"
            assert row_db.tipologia == ["a", "b"]
            assert row_db.data_value.get('stato') == "Caricato"
            assert row_db.get('data_value.stato').startswith("Car") is True
            assert row_db.stato == "caricato"
            assert row_db.list_order == id

            row_db.selection_value("stato", "done", 'Done')
            row_db.selection_value("tipologia", ["a", "c"], ["A", "C"])

            row_upd = await self.row_model.update(row_db)

            assert row_upd.nrRiga == row.nrRiga
            assert row_upd.rec_name == f"{v_doc.rec_name}.{row.nrRiga}"
            assert row_upd.tipologia == ["a", "c"]
            assert row_upd.data_value.get('stato') == "Done"
            assert row_upd.data_value.get('tipologia') == ["A", "C"]
            assert row_upd.get('data_value.stato').startswith("Do") is True
            assert row_upd.stato == "done"
            assert row_db.list_order == id

        documento = await self.virtual_doc_model.insert(v_doc)

        assert documento.dec_nome == "Test Dec"
        assert documento.data_value['ammImpEuro'] == locale.format_string(
            '%.2f', 1446.16, True)
        assert documento.anomalia_gestita is False
        assert documento.data_value['dtRegistrazione'] == "24/05/2022"
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
    """
    test_form_2_formio_schema_doc.json
    "test_form_2_formio_schema_doc_riga.json
    """
    schema_list = await get_formio_doc_schema()
    schema_list2 = await get_formio_doc_riga_schema()
    schema_list3 = await get_formio_doc_schema2()
    cfg = await OzonEnv.readfilejson(get_config_path())
    env = OzonEnv(cfg)
    await env.init_env()
    env.params = {"current_session_token": "BA6BA930"}
    await env.session_app()
    doc_schema = await env.get('component').new(data=schema_list[0])
    doc_schema = await env.get('component').insert(doc_schema)
    assert doc_schema.rec_name == "documento"
    doc_schema3 = await env.get('component').new(data=schema_list3[0])
    doc_schema3 = await env.get('component').insert(doc_schema3)
    assert doc_schema3.rec_name == "documento_beni_servizi"
    assert doc_schema3.data_model == "documento"
    doc_riga_schema = await env.get('component').new(data=schema_list2[0])
    doc_riga_schema = await env.get('component').insert(doc_riga_schema)
    assert doc_riga_schema.rec_name == "riga_doc"


@pytestmark
async def test_init_worker_ok():
    cfg = await MockWorker1.readfilejson(get_config_path())
    worker = MockWorker1(cfg)
    res = await worker.make_app_session(
        use_cache=True,
        redis_url="redis://localhost:10001",
        params={
            "current_session_token": "BA6BA930",
            "topic_name": "test_topic",
            "document_type": "standard",
            "model": "documento_beni_servizi",
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
    assert res.data['test_topic']['model'] == "documento_beni_servizi"
    assert res.data['documento_beni_servizi']['stato'] == "caricato"


@pytestmark
async def test_init_worker_fail():
    cfg = await MockWorker1.readfilejson(get_config_path())
    worker = MockWorker1(cfg)
    res = await worker.make_app_session(
        use_cache=True,
        redis_url="redis://localhost:10001",
        params={
            "current_session_token": "BA6BA930",
            "topic_name": "test_topic",
            "document_type": "standard",
            "model": "documento_beni_servizi",
            "session_is_api": False,
            "action_next_page": {
                "success": {"form": "/open/doc"},
            }
        }
    )
    assert res.fail is True
    print(res.msg)
    assert res.msg == "Errore Duplicato rec_name: DOC99999.1"
    assert res.data['test_topic']["error"] is True
    assert res.data['test_topic']["done"] is True
    assert res.data['test_topic']['next_page'] == "self"
    assert res.data['test_topic']['model'] == "documento_beni_servizi"
