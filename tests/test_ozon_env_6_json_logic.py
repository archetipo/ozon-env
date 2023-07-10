import pytest
from test_common import *
from ozonenv.core.ModelMaker import ModelMaker, BasicModel
from ozonenv.core.BaseModels import CoreModel
from pydantic._internal._model_construction import ModelMetaclass
from ozonenv.OzonEnv import OzonWorkerEnv, OzonEnv, BasicReturn
from datetime import *
from dateutil.parser import *
import traceback
import locale
import logging
from test_ozon_env_5_basic_for_worker import MockWorker1

pytestmark = pytest.mark.asyncio


class MockWorker3(MockWorker1):

    async def process_document(self, data_doc) -> CoreModel:
        query = {
            "$and": [
                {"active": True},
                {"document_type": {
                    "$in": ["ordine"]}},
                {"numeroRegistrazione": 9},
                {"annoRif": 2022}
            ]
        }
        doc = await self.p_model.load(query)
        assert self.p_model.model.conditional() == {}
        assert self.p_model.model.logic() == {}
        return doc


@pytestmark
async def test_check_logic():
    worker = MockWorker3()
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
    assert res.data['test_topic']['next_page'] == "/open/doc/DOC99998"
    assert res.data['test_topic']['model'] == "documento_beni_servizi"
    assert res.data['documento_beni_servizi']['stato'] == "caricato"
