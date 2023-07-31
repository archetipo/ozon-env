import asyncio
import copy
import json
import logging
# from ozonenv.core.cache.cache import get_cache
import os
import time as time_
from importlib.machinery import SourceFileLoader
from os.path import dirname, exists

import aiofiles
from aiopath import AsyncPath
from starlette.concurrency import run_in_threadpool

from ozonenv.core.BaseModels import (
    DbViewModel,
    Component,
    Session,
    Settings,
    AttachmentTrash,
    CoreModel,
    Dict,
    BasicModel,
)
from ozonenv.core.OzonClient import OzonClient
from ozonenv.core.OzonModel import OzonModelBase, BasicReturn
from ozonenv.core.cache.cache_utils import stop_cache  # , init_cache
from ozonenv.core.db.mongodb_utils import (
    connect_to_mongo,
    close_mongo_connection,
    DbSettings,
    Mongo,
    Collection,
    _DocumentType,
)
from ozonenv.core.exceptions import SessionException
from ozonenv.core.i18n import _
from ozonenv.core.i18n import update_translation

logger = logging.getLogger(__file__)

MAIN_CACHE_TIME = 800

base_model_path = dirname(__file__)


class OzonEnvBase:
    def __init__(
            self,
            cfg: dict = None,
            upload_folder: str = "",
            cls_model=OzonModelBase,
    ):
        if cfg is None:
            cfg = {}
        self.orm: OzonOrm
        self.db: Mongo
        self.ozon_client: OzonClient
        if not cfg:
            self.config_system = {
                "app_code": os.getenv("APP_CODE"),
                "mongo_user": os.getenv("MONGO_USER"),
                "mongo_pass": os.getenv("MONGO_PASS"),
                "mongo_url": os.getenv("MONGO_URL"),
                "mongo_db": os.getenv("MONGO_DB"),
                "mongo_replica": os.getenv("MONGO_REPLICA"),
                "models_folder": os.getenv("MODELS_FOLDER", "/models"),
            }
        else:
            self.config_system = cfg.copy()
        self.db_settings = DbSettings(**self.config_system)
        self.model = ""
        self.models: Dict[str, cls_model] = {}
        self.params = {}
        self.session_is_api = False
        self.user_session: CoreModel
        self.session_token = None
        self.use_cache = False
        self.cache_index = "ozon_env"
        self.redis_url = ""
        self.orm_from_cache: bool = False
        self.upload_folder: str = upload_folder
        self.models_folder: str = self.config_system.get(
            "models_folder", "/models"
        )
        self.is_db_local = True
        self.app_code = self.config_system.get("app_code")
        self.cls_model = cls_model

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

    async def set_lang(self, lang="it", update=False):
        self.lang = lang
        await run_in_threadpool(update_translation, lang)
        # locale.setlocale(locale.LC_NUMERIC, locale.locale_alias[lang])
        if update:
            await self.orm.set_lang()

    async def insert_update_component(self, schema):
        """
        :param schema: json dict of component with formio schema
        :return: Component record
        """
        c_model = self.get('component')
        model_name = schema.get("rec_name")
        component = await c_model.load({"rec_name": model_name})
        new_component = await c_model.new(data=schema)
        if not component:
            res = await c_model.insert(new_component)
            await self.orm.add_model(model_name)
        else:
            res = await c_model.update(new_component)
            await self.orm.update_model(schema, component)
        return res

    def get(self, model_name) -> OzonModelBase:
        return self.models.get(model_name)

    def get_collection(self, collection) -> Collection[_DocumentType]:
        return self.db.engine.get_collection(collection)

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
        if self.user_session.is_public:
            return None
        if model_name not in self.models:
            await self.orm.add_model(
                model_name, virtual=virtual, data_model=data_model
            )
        return self.get(model_name)

    async def add_static_model(
            self, model_name: str, model_class: BasicModel,
            private: bool = False
    ) -> OzonModelBase:
        return await self.orm.add_static_model(
            model_name, model_class, private
        )

    async def connect_db(self):
        self.db = await connect_to_mongo(self.db_settings)

    async def close_db(self):
        await close_mongo_connection()

    async def init_orm(
            self,
            db=None,
            local_model: dict = None,
            local_model_private: list = None,
    ):
        if local_model is None:
            local_model = {}
        if local_model_private is None:
            local_model_private = []
        if db:
            self.db = db
            self.is_db_local = False
        else:
            await self.connect_db()
        await self.set_lang()
        self.orm = OzonOrm(self, cls_model=self.cls_model)
        if local_model:
            for k, v in local_model.items():
                self.orm.orm_models.append(k)
                self.orm.orm_static_models_map[k] = v
                if k in local_model_private:
                    self.orm.add_private_model(k)

    async def init_env(
            self,
            db: Mongo = None,
            local_model: dict = None,
            local_model_private: list = None,
    ):
        if local_model is None:
            local_model = {}
        if local_model_private is None:
            local_model_private = []
        await self.init_orm(
            db=db,
            local_model=local_model,
            local_model_private=local_model_private,
        )
        await self.orm.init_models()

    async def close_env(self):
        if self.is_db_local:
            await self.close_db()
        if self.use_cache:
            await stop_cache()

    async def make_app_session(
            self,
            params: dict,
            use_cache=True,
            cache_idx="ozon_env",
            redis_url="redis://redis_cache",
            db=None,
            local_model={},
    ) -> BasicReturn:
        try:
            self.params = copy.deepcopy(params)
            self.use_cache = use_cache
            self.cache_index = cache_idx
            self.redis_url = redis_url
            await self.init_env(db=db, local_model=local_model)
            res = await self.session_app()
            await self.close_env()
            return res
        except Exception as e:
            logger.exception(e)
            return self.fail_response(str(e))

    async def session_app(self) -> BasicReturn:
        self.session_is_api = self.params.get("session_is_api", False)
        self.session_token = self.params.get("current_session_token")
        await self.orm.init_session(self.session_token)
        if not self.upload_folder:
            self.upload_folder = self.orm.app_settings.upload_folder
        self.user_session = self.orm.user_session
        if not self.user_session:
            return self.fail_response(
                _("Token %s not allowed") % self.session_token
            )
        return BasicReturn(fail=False, msg="Done", data={})


class OzonOrm:
    def __init__(self, env: OzonEnvBase, cls_model=OzonModelBase):
        self.env: OzonEnvBase = env
        self.lang = env.lang
        self.db: Mongo = env.db
        self.config_system = env.config_system.copy()
        self.user_session: Session = None
        self.list_auto_models = []
        self.orm_models = [
            "component",
            "session",
            "attachmenttrash",
            "settings",
        ]
        self.orm_static_models_map = {
            "component": Component,
            "session": Session,
            "attachmenttrash": AttachmentTrash,
            "settings": Settings,
        }
        self.db_models = []
        self.orm_sys_models = ["component", "session", "settings"]
        self.private_models = ["settings"]
        self.models_path = self.env.models_folder
        self.app_settings: Settings = None
        self.app_code = self.env.app_code
        self.cls_model = cls_model

    def add_private_model(self, name):
        if name not in self.private_models:
            self.private_models.append(name)

    async def add_static_model(
            self, model_name: str, model_class: BasicModel,
            private: bool = False
    ) -> OzonModelBase:
        _model_name = model_name.replace(" ", "").strip().lower()
        self.orm_models.append(_model_name)
        self.orm_static_models_map[model_name] = model_class
        self.env.models[_model_name] = self.cls_model(
            _model_name,
            self,
            static=model_class,
        )
        await self.env.models[_model_name].init_model()
        await self.env.models[_model_name].init_unique()
        if private:
            self.add_private_model(_model_name)
        return self.env.models[_model_name]

    async def init_db_models(self):
        self.db_models = await self.get_collections_names()
        self.app_settings = await self.init_settings(self.app_code)

    async def init_models(self):
        # self.models_path = self.config_system.get("models_folder", "/models")
        await self.init_db_models()
        await AsyncPath(self.models_path).mkdir(parents=True, exist_ok=True)
        await AsyncPath(f"{self.models_path}/__init__.py").touch(exist_ok=True)
        self.list_auto_models = AsyncPath(self.models_path).glob("*.py")
        for main_model in self.orm_models:
            if main_model not in self.env.models:
                await self.make_model(main_model)

        for db_model in self.db_models:
            if db_model not in list(self.env.models.keys()):
                home = AsyncPath(f"{self.models_path}/{db_model}.py")
                if await home.exists():
                    await self.import_module_model(db_model)
                    model = self.orm_static_models_map[db_model]
                    component = await self.env.get("component").load(
                        {
                            '$and': [
                                {"rec_name": db_model},
                                {
                                    'update_datetime': {
                                        '$gt': model.get_version()
                                    }
                                },
                            ]
                        }
                    )
                    if component:
                        await self.update_model(
                            component.get_dict_copy(), component
                        )
                    else:
                        await self.make_model(db_model)
                else:
                    await self.add_model(db_model)

    async def get_collections_names(self, query={}):
        if not query:
            query = {"name": {"$regex": r"^(?!system\.)"}}
        collection_names = await self.db.engine.list_collection_names(
            filter=query
        )
        q = {
            "$and": [
                {"active": True},
                {"rec_name": {"$nin": collection_names}},
            ]
        }
        coll = self.db.engine.get_collection('component')
        res = await coll.distinct("rec_name", q)
        collection_names += res
        return collection_names

    async def init_settings(self, app_code):
        logger.info(f"init app: {app_code}")
        query = {"rec_name": app_code}
        coll_settings = self.env.get_collection("settings")
        db_settings = await coll_settings.find_one(query)
        if db_settings.get("_id"):
            db_settings.pop("_id")
        return Settings(
            **db_settings,
            exclude_none=True,
            exclude_unset=True,
            check_fields=False,
        )

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

    async def runcmd(self, cmd):
        # for security reason check the command
        if not cmd.startswith("datamodel-codegen --input"):
            return
        res = True
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        await proc.communicate()

        logger.info(f"[{cmd!r} exited with {proc.returncode}]")

        return res

    async def import_module_model(self, model_name):
        def camel(snake_str):
            names = snake_str.split("_")
            return "".join([*map(str.title, names)])

        def _getattribute(obj, name):
            for subpath in name.split("."):
                parent = obj
                obj = getattr(obj, subpath)
            return obj, parent

        mclass = camel(model_name)
        module_name = f"{model_name}"
        file_path = f"{self.models_path}/{model_name}.py"
        module = SourceFileLoader(module_name, file_path).load_module()
        model, parent = _getattribute(module, mclass)
        self.orm_static_models_map[model_name] = model

    async def make_local_model(self, mod, version):
        jdata = mod.mm.model.schema_json(indent=2)
        async with aiofiles.open(f"/tmp/{mod.name}.json", "w+") as mod_file:
            await mod_file.write(jdata)
        res = await self.runcmd(
            f"datamodel-codegen --input /tmp/{mod.name}.json"
            f" --output {self.models_path}/{mod.name}.py "
            f" --output-model-type pydantic_v2.BaseModel "
            f"--base-class ozonenv.core.BaseModels.BasicModel"
        )
        if not res:
            return
        tmp = f"""
    
    @classmethod
    def get_version(cls):
        return '{version}'
        
    @classmethod
    def get_unique_fields(cls):
        return {mod.mm.unique_fields}
        
    @classmethod
    def computed_fields(cls):
        return {mod.mm.computed_fields}
    
    @classmethod
    def no_clone_field_keys(cls):
        return {mod.mm.no_clone_field_keys}
    
    @classmethod
    def tranform_data_value(cls):
        return {mod.mm.tranform_data_value}    
    
    @classmethod
    def fields_limit_value(cls):
        return {mod.mm.fields_limit_value}     
    
    @classmethod
    def create_task_action(cls):
        return {mod.mm.create_task_action}
    
    @classmethod
    def fields_properties(cls):
        return {mod.mm.fields_properties}
        
    @classmethod
    def default_hidden_fields(cls):
        return {mod.mm.default_hidden_fields}

    @classmethod
    def default_readonly_fields(cls):
        return {mod.mm.default_readonly_fields}
    
    @classmethod
    def default_required_fields(cls):
        return {mod.mm.default_required_fields}   
         
    @classmethod
    def filter_keys(cls):
        return {mod.mm.filter_keys}  
         
    @classmethod
    def config_fields(cls):
        return {mod.mm.config_fields}
         
    @classmethod
    def components_ext_data_src(cls):
        return {mod.mm.components_ext_data_src}
    
    @classmethod
    def get_data_model(cls):
        return "{mod.mm.data_model}"
    
    @classmethod
    def conditional(cls) -> {{str, dict}}:
        return {mod.mm.conditional}

    @classmethod
    def logic(cls) -> {{str, list}}:
        return {mod.mm.logic}
    
    @classmethod
    def conditional(cls) -> {{str, dict}}:
        return {mod.mm.conditional}

    @classmethod
    def logic(cls) -> {{str, list}}:
        return {mod.mm.conditional}
"""
        async with aiofiles.open(
                f"{self.models_path}/{mod.name}.py", "a+"
        ) as mod_file:
            await mod_file.write(tmp)

    async def init_model_and_write_code(
            self, model_name, data_model, virtual, schema, component
    ):
        session_model = model_name == "session"
        mod = self.cls_model(
            model_name,
            self,
            data_model=data_model,
            static=self.orm_static_models_map.get(model_name, None),
            virtual=virtual,
            schema=schema,
            session_model=session_model,
        )
        await mod.init_model()
        await self.make_local_model(mod, component.update_datetime.isoformat())

    async def add_model(self, model_name, virtual=False, data_model=""):
        schema = {}
        if not virtual:
            component = await self.env.get("component").load(
                {"rec_name": model_name}
            )
            if component:
                schema = component.get_dict_copy()
        if (
                schema
                and model_name not in list(self.orm_static_models_map.keys())
                and not virtual
        ):
            if not exists(f"{self.models_path}/{model_name}.py"):
                await self.init_model_and_write_code(
                    model_name, data_model, virtual, schema, component
                )
            await self.import_module_model(model_name)
        await self.make_model(
            model_name, schema=schema, virtual=virtual, data_model=data_model
        )
        self.db_models = await self.get_collections_names()

    async def make_model(
            self, model_name, schema={}, virtual=False, data_model=""
    ):
        if model_name in list(self.orm_static_models_map.keys()) or virtual:
            session_model = model_name == "session"
            if not data_model and schema:
                data_model = schema.get("data_model", "")
            if (
                    not data_model
                    and not virtual
                    and self.orm_static_models_map[model_name].get_data_model()
            ):
                data_model = self.orm_static_models_map[
                    model_name
                ].get_data_model()
            self.env.models[model_name] = self.cls_model(
                model_name,
                self,
                data_model=data_model,
                static=self.orm_static_models_map.get(model_name, None),
                virtual=virtual,
                schema=schema,
                session_model=session_model,
            )
            await self.env.models[model_name].init_model()
            if not virtual:
                if model_name not in self.db_models:
                    await self.env.models[model_name].init_unique()

    async def update_model(self, schema, component):
        if schema.get("rec_name") in self.orm_static_models_map:
            self.orm_static_models_map.pop(schema.get("rec_name"))
        await self.init_model_and_write_code(
            schema.get("rec_name"), "", False, schema, component
        )
        await self.import_module_model(schema.get("rec_name"))
        await self.make_model(
            schema.get("rec_name"),
            schema=schema,
            virtual=False,
            data_model="",
        )

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
        self.setting_app = orm.app_settings.copy()
        self.db: Mongo = orm.env.db
        self.mm_from_cache = False
        self.use_cache = False
        self.private_models = ["session", "settings"]
        super(OzonModel, self).__init__(
            model_name=model_name,
            setting_app=self.setting_app,
            data_model=data_model,
            session_model=session_model,
            virtual=virtual,
            static=static,
            schema=schema,
        )

    @property
    def user_session(self):
        return self.orm.user_session

    def init_status(self):
        if self.user_session and self.user_session.is_public:
            if self.name.lower() in self.orm.private_models:
                raise SessionException(detail="Permission Denied")
        super().init_status()

    def chk_write_permission(self) -> bool:
        res = super().chk_write_permission()
        if self.user_session and self.user_session.is_public:
            return False
        return res
