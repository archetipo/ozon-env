import copy
import json
from ozonenv.core.db.mongodb_utils import (
    connect_to_mongo,
    close_mongo_connection,
    DbSettings,
    Mongo,
)
import time as time_
from ozonenv.core.OzonModel import OzonModelBase, BasicReturn
from ozonenv.core.OzonClient import OzonClient
from ozonenv.core.BaseModels import (
    DbViewModel,
    Component,
    Session,
    AttachmentTrash,
    CoreModel,
)
import logging
import aiofiles
from dateutil.parser import parse
from starlette.concurrency import run_in_threadpool
from ozonenv.core.i18n import update_translation
from ozonenv.core.i18n import _
from datetime import datetime, date
import datetime as dt
import locale

logger = logging.getLogger(__file__)


class OzonEnvBase:
    def __init__(self, cfg, upload_folder=""):
        self.config_system = {}
        self.orm: OzonOrm
        self.db: Mongo
        self.ozon_client: OzonClient
        self.config_system = cfg
        self.settings = DbSettings(**self.config_system)
        self.model = ""
        self.models = {}
        self.params = {}
        self.session_is_api = False
        self.user_session: CoreModel
        self.session_token = None
        self.upload_folder = upload_folder
        if not upload_folder:
            self.upload_folder = cfg["upload_folder"]

    @classmethod
    async def readfilejson(cls, cfg_file):
        async with aiofiles.open(cfg_file, mode="r") as f:
            data = await f.read()
        return json.loads(data)

    @classmethod
    def get_formatted_metrics(cls, start_time: float, time_division=0):
        if time_division > 0:
            process_time = (time_.monotonic() - start_time) / time_division
        else:
            process_time = time_.monotonic() - start_time
        return "{0:.2f}".format(process_time)

    @classmethod
    def fail_response(cls, err, err_details="", data={}):
        if "err_details" not in data:
            data["err_details"] = err_details
        return BasicReturn(fail=True, msg=err, data=data)

    @classmethod
    def success_response(cls, msg, data={}):
        return BasicReturn(fail=False, msg=msg, data=data)

    @classmethod
    def get_value_for_select_list(cls, list_src, key, label_key="label"):
        for item in list_src:
            if item.get("value") == key:
                return item.get(label_key)
        return ""

    async def set_lang(self, lang="it", upldate=False):
        self.lang = lang
        await run_in_threadpool(update_translation, lang)
        if upldate:
            await self.orm.set_lang()

    def get(self, model_name) -> OzonModelBase:
        return self.models.get(model_name)

    async def add_schema(self, schema: dict) -> OzonModelBase:
        component_model = self.models.get("component")
        component = await component_model.new(schema)
        component = await component_model.insert(component)
        if not component.data_model:
            await self.orm.add_model(component.rec_name, virtual=False)
            return self.get(component.rec_name)
        else:
            return self.get(component.data_model)

    async def add_model(
            self, model_name, virtual=False, data_model=""
    ) -> OzonModelBase:
        if model_name not in self.models:
            await self.orm.add_model(
                model_name, virtual=virtual, data_model=data_model
            )
        return self.get(model_name)

    async def add_static_model(
            self, model_name: str, model_class: CoreModel
    ) -> OzonModelBase:
        return await self.orm.add_static_model(model_name, model_class)

    async def connect_db(self):
        self.db = await connect_to_mongo(self.settings)

    async def close_db(self):
        await close_mongo_connection()

    def make_data_value(self, val, cfg):
        if cfg["type"] is datetime or cfg["type"] is dt.datetime:
            res = self._readable_datetime(val)
        elif cfg["type"] is date or cfg["type"] is dt.date:
            res = self._readable_date(val)
        elif cfg["type"] is float:
            res = self.readable_float(val, dp=cfg["dp"])
        else:
            res = val
        return res

    def _readable_datetime(self, val):
        if isinstance(val, str):
            return parse(val).strftime(self.config_system["ui_datetime_mask"])
        else:
            return val.strftime(self.config_system["ui_datetime_mask"])

    def _readable_date(self, val):
        if isinstance(val, str):
            return parse(val).strftime(self.config_system["ui_date_mask"])
        else:
            return val.strftime(self.config_system["ui_date_mask"])

    def readable_float(self, val, dp=2, g=True):
        if isinstance(val, str):
            val = float(val)
        return locale.format_string(f"%.{dp}f", val, g)

    async def init_env(self):
        await self.connect_db()
        await self.set_lang()
        self.orm = OzonOrm(self)

    async def make_app_session(self, params: dict) -> BasicReturn:
        try:
            self.params = copy.deepcopy(params)
            await self.init_env()
            res = await self.session_app()
            await self.close_db()
            return res
        except Exception as e:
            logger.exception(e)
            return self.fail_response(str(e))

    async def session_app(self) -> BasicReturn:
        self.session_is_api = self.params.get("session_is_api", False)
        self.session_token = self.params.get("current_session_token")
        await self.orm.init_models()
        await self.orm.init_session(self.session_token)
        self.user_session = self.orm.user_session
        if not self.user_session:
            return self.fail_response(
                _("Token %s not allowed") % self.session_token
            )
        self.ozon_client = OzonClient.create(
            self.session_token, is_api=self.session_is_api
        )
        return BasicReturn(fail=False, msg="Done", data={})


class OzonOrm:
    def __init__(self, env: OzonEnvBase):
        self.env: OzonEnvBase = env
        self.lang = env.lang
        self.db: Mongo = env.db
        self.user_session: CoreModel = None
        self.orm_models = ["component", "session", "attachmenttrash"]
        self.orm_static_models_map = {
            "component": Component,
            "session": Session,
            "attachmenttrash": AttachmentTrash,
        }
        self.orm_sys_models = ["component", "session"]

    async def add_static_model(
            self, model_name: str, model_class: CoreModel
    ) -> OzonModelBase:
        _model_name = model_name.replace(" ", "").strip().lower()
        self.orm_models.append(_model_name)
        self.orm_static_models_map[model_name] = model_class
        self.env.models[_model_name] = OzonModel(
            _model_name,
            self,
            static=model_class,
        )
        await self.env.models[_model_name].init_unique()
        return self.env.models[_model_name]

    async def init_models(self):
        self.db_models = await self.get_collections_names()
        for main_model in self.orm_models:
            if main_model not in self.env.models:
                await self.make_model(main_model)

        for db_model in self.db_models:
            if db_model not in self.env.models:
                await self.add_model(db_model)

    async def get_collections_names(self, query={}):
        if not query:
            query = {"name": {"$regex": r"^(?!system\.)"}}
        collection_names = await self.db.engine.list_collection_names(
            filter=query
        )
        return collection_names

    async def create_view(self, dbviewcfg: DbViewModel):
        if (
                not dbviewcfg.force_recreate
                and dbviewcfg.name in self.db.engine.collection
        ):
            return False
        collections = await self.get_collections_names()
        if dbviewcfg.force_recreate and dbviewcfg.name in collections:
            self.db.engine.drop_collection(dbviewcfg.name)
        try:
            await self.db.engine.command(
                {
                    "create": dbviewcfg.name,
                    "viewOn": dbviewcfg.model,
                    "pipeline": dbviewcfg.pipeline,
                }
            )
            return True
        except Exception as e:
            logger.error(f" Error create view {dbviewcfg.name} - {e}")
            return False

    async def init_session(self, token):
        self.user_session = await self.env.get("session").load(
            {"token": token}
        )

    async def add_model(self, model_name, virtual=False, data_model=""):
        schema = {}
        if not virtual:
            component = await self.env.get("component").load(
                {"rec_name": model_name}
            )
            if component:
                schema = component.get_dict_copy()
        await self.make_model(
            model_name, schema=schema, virtual=virtual, data_model=data_model
        )
        self.db_models = await self.get_collections_names()

    async def make_model(
            self, model_name, schema={}, virtual=False, data_model=""
    ):

        if (
                model_name in list(self.orm_static_models_map.keys())
                or schema
                or virtual
        ):
            session_model = model_name == "session"
            if not data_model and schema:
                data_model = schema.get("data_model", "")
            self.env.models[model_name] = OzonModel(
                model_name,
                self,
                data_model=data_model,
                static=self.orm_static_models_map.get(model_name, None),
                virtual=virtual,
                schema=schema,
                session_model=session_model,
            )
            if not virtual:
                if model_name not in self.db_models:
                    await self.env.models[model_name].init_unique()

    async def set_lang(self):
        self.lang = self.env.lang
        for model_name, model in self.env.models.items():
            await model.set_lang()


class OzonModel(OzonModelBase):
    def __init__(
            self,
            model_name,
            orm: OzonOrm,
            data_model="",
            session_model=False,
            virtual=False,
            static: CoreModel = None,
            schema={},
    ):
        self.orm: OzonOrm = orm
        self.env: OzonEnvBase = orm.env
        self.db: Mongo = orm.env.db
        super(OzonModel, self).__init__(
            model_name,
            data_model=data_model,
            session_model=session_model,
            virtual=virtual,
            static=static,
            schema=schema,
        )

    def init_model(self):
        super(OzonModel, self).init_model()
