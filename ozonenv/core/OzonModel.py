import copy
import json
import locale
import logging
import re
from datetime import datetime, timedelta
from typing import Any

import bson
import pydantic
import pymongo
from dateutil.parser import parse
from pydantic._internal._model_construction import ModelMetaclass

from exceptions import SessionException
from ozonenv.core.BaseModels import (
    Component,
    BasicModel,
    CoreModel,
    Settings,
    BasicReturn,
    DictRecord,
    default_list_metadata,
    default_list_metadata_fields_update,
)
from ozonenv.core.ModelMaker import ModelMaker
from ozonenv.core.db.BsonTypes import JsonEncoder
from ozonenv.core.i18n import _
from ozonenv.core.utils import is_json

logger = logging.getLogger(__name__)


class OzonMBase:
    def __init__(
        self,
        model_name,
        setting_app={},
        data_model="",
        session_model=False,
        virtual=False,
        static: BasicModel = None,
        schema={},
    ):
        """
        :param model_name: the name of model must be unique
        :param setting_app: base App settings
        :param data_model: the name of data model in case of virtual model
                           use this collection to store o retreive data.
        :param session_model: True/False if the model is Session or
                              a subclass of Session Model
        :param virtual: True/False if is virtual_model create a model from a
                        generic data dictionary, without the schema
        :param static: ModelClass, if the model is in python Class you need to
                    set model as a static model, when object init the data
                    model, use directly this model class insted to run model
                    maker.
        :param schema: formio form schema, mandatory if
        """
        self.name = model_name
        self.setting_app: Settings = setting_app
        self.virtual = virtual
        self.static: BasicModel = static
        self.instance: BasicModel
        if self.virtual:
            self.data_model = data_model
        else:
            self.data_model = data_model or model_name
        self.schema = copy.deepcopy(schema)
        self.session_model = session_model
        self.is_session_model = session_model
        self.model_meta: ModelMetaclass = None
        self.modelr: CoreModel = None
        self.mm: ModelMaker = None
        self.model: BasicModel
        self.name_allowed = re.compile(r"^[A-Za-z0-9._~():+-]*$")
        self.sort_dir = {"asc": 1, "desc": -1}
        self.default_sort_str = "list_order:desc,"
        self.default_domain = {"active": True, "deleted": 0}
        self.archived_domain = {"active": False, "deleted": {"$gt": 0}}
        self.transform_config = {}
        self.status: BasicReturn = BasicReturn(
            **{"fail": False, "msg": "", "data": {}}
        )
        self.tranform_data_value = {}
        self.rheader = False
        self.rfooter = False
        self.send_mail_create = False
        self.send_mail_create = False
        self.form_disabled = False
        self.no_submit = False
        self.queryformeditable = {}

        self.init_schema_properties()

    def init_schema_properties(self):
        if self.schema.get("properties", {}):
            for k, v in self.schema.get("properties", {}).items():
                match k:
                    case ["sort"]:
                        self.default_sort_str = v
                    case [
                        "send_mail_create",
                        "send_mail_update",
                        "rfooter",
                        "rheader",
                        "form_disabled",
                        "no_submit",
                    ]:
                        setattr(self, k, v == "1")
                    case ["queryformeditable"]:
                        self.queryformeditable = is_json(v)

    async def init_model(self):
        self.mm = ModelMaker(self.name)
        if self.static:
            self.model = self.static
            self.tranform_data_value = self.model.tranform_data_value()
        elif not self.static and not self.virtual:
            c_maker = ModelMaker("component")
            c_maker.model = Component
            c_maker.new()
            self.mm.from_formio(self.schema)

    @classmethod
    def _value_type(cls, v):
        type_def = {
            "int": int,
            "string": str,
            "float": float,
            "dict": dict,
            "list": list,
            "date": datetime,
        }
        s = v
        if not isinstance(v, str):
            s = str(v)
        regex = re.compile(
            r"(?P<dict>\{[^{}]+\})|(?P<list>\[[^]]+\])|(?P<float>\d*\.\d+)"
            r"|(?P<int>\d+)|(?P<string>[a-zA-Z]+)"
        )
        regex_dt = re.compile(r"(\d{4}-\d{2}-\d{2})[A-Z]+(\d{2}:\d{2}:\d{2})")
        dtr = regex_dt.search(s)
        if dtr:
            return datetime
        else:
            rgx = regex.search(s)
            if not rgx:
                return str
            if s in ["false", "true"]:
                return bool
            types_d = []
            for match in regex.finditer(s):
                types_d.append(match.lastgroup)
            if len(types_d) > 1:
                return str
            else:
                return type_def.get(rgx.lastgroup)

    def make_data_value(self, val, cfg):
        if cfg["type"] == "datetime":
            res = self._readable_datetime(val)
        elif cfg["type"] == "date":
            res = self._readable_date(val)
        elif cfg["type"] == "float":
            res = self.readable_float(val, dp=cfg["dp"])
        else:
            res = val
        return res

    def _readable_datetime(self, val):
        if isinstance(val, str):
            return parse(val).strftime(self.setting_app.ui_datetime_mask)
        else:
            return val.strftime(self.setting_app.ui_datetime_mask)

    def _readable_date(self, val):
        if isinstance(val, str):
            return parse(val).strftime(self.setting_app.ui_date_mask)
        else:
            return val.strftime(self.setting_app.ui_date_mask)

    def readable_float(self, val, dp=2, g=True):
        if isinstance(val, str):
            val = float(val)
        return locale.format_string(f"%.{dp}f", val, g)

    def _make_from_dict(self, dict_data):
        res_dict = {}
        for k, v in dict_data.items():
            if isinstance(v, dict):  # For DICT
                if not k == "data_value":
                    res_dict[k] = self._make_from_dict(v)
                else:
                    res_dict[k] = v
            elif isinstance(v, list):  # For LIST
                res_dict[k] = []
                for i in v:
                    if isinstance(i, dict):
                        res_dict[k].append(self._make_from_dict(i))
                    else:
                        res_dict[k].append(i)
            else:
                if "data_value" not in res_dict or not isinstance(
                    res_dict, dict
                ):
                    res_dict["data_value"] = {}
                if k in self.tranform_data_value:
                    res_dict["data_value"][k] = self.make_data_value(
                        v, self.tranform_data_value[k]
                    )
                elif self._value_type(v) is datetime:
                    res_dict["data_value"][k] = self.make_data_value(
                        v, {"type": datetime}
                    )
                elif self._value_type(v) is float:
                    res_dict["data_value"][k] = self.make_data_value(
                        v, {"type": float, "dp": 2}
                    )
                res_dict[k] = v

        return res_dict.copy()

    def load_data(self, data):
        if not self.virtual:
            self.modelr = self.model(**data)
        else:
            self.mm = ModelMaker(self.data_model)
            if self.transform_config:
                self.tranform_data_value = self.transform_config.copy()
            # if data.get("_id"):
            #     data.pop("_id")
            self.mm.from_data_dict(data)

            self.modelr = self.mm.new()
        if not self.is_session_model and not self.modelr.rec_name:
            self.modelr.rec_name = f"{self.data_model}.{self.modelr.id}"


class OzonModelBase(OzonMBase):
    @property
    def message(self):
        return self.status.msg

    @property
    def unique_fields(self):
        return self.model.unique_fields

    def error_status(self, msg, data):
        self.status.fail = True
        self.status.msg = msg
        self.status.data = data

    def init_status(self):
        self.status.fail = False
        self.status.msg = ""
        self.status.data = {}

    def chk_write_permission(self) -> bool:
        return True

    def is_error(self):
        return self.status.fail

    def get_domain(self, domain={}):
        _domain = self.default_domain.copy()
        _domain.update(domain)
        return _domain

    def get_domain_archived(self, domain={}):
        _domain = self.archived_domain.copy()
        _domain.update(domain)
        return _domain

    async def set_lang(self):
        self.lang = self.orm.lang

    def eval_sort_str(self, sortstr="") -> list[tuple]:
        """
        eval sort string in sort rule
        :param sortstr: eg. list_order:asc,rec_name:desc
        :return: List(Tuple) eg. [('list_order', 1),('rec_name', -1)]
        """
        if not sortstr:
            sortstr = self.default_sort_str
        sort_rules = sortstr.split(",")
        sort = {}
        for rule_str in sort_rules:
            if rule_str:
                rule_list = rule_str.split(":")
                if len(rule_list) > 1:
                    sort[rule_list[0]] = self.sort_dir[rule_list[1]]
        return sort

    def get_dict(self, rec: CoreModel, exclude=[]) -> CoreModel:
        return rec.get_dict(exclude=exclude)

    def get_dict_record(self, rec: CoreModel, rec_name="") -> DictRecord:
        dictd = self.get_dict(rec, exclude=default_list_metadata + ["_id"])
        if rec_name:
            dictd["rec_name"] = rec_name
        dat = DictRecord(
            model="virtual", rec_name=rec_name, data=copy.deepcopy(dictd)
        )
        return dat

    def set_user_data(self, record: CoreModel, user={}) -> CoreModel:
        record.owner_uid = user.get("user.uid")
        record.owner_name = user.get("user.full_name", "")
        record.owner_mail = user.get("user.mail", "")
        record.owner_sector = user.get("sector", "")
        record.owner_sector_id = user.get("sector_id", 0)
        record.owner_personal_type = user.get("user.tipo_personale", "")
        record.owner_job_title = user.get("user.qualifica", "")
        record.owner_function = user.get("function", "")
        return record

    async def init_unique(self):
        for field in self.model.get_unique_fields():
            await self.set_unique(field)

    async def set_unique(self, field_name):
        self.init_status()
        component_coll = self.db.engine.get_collection(self.data_model)
        await component_coll.create_index([(field_name, 1)], unique=True)

    async def count_by_filter(self, domain: dict) -> int:
        self.init_status()
        coll = self.db.engine.get_collection(self.data_model)
        val = await coll.count_documents(domain)
        if not val:
            val = 0
        return int(val)

    async def count(self, domain={}) -> int:
        self.init_status()
        if not domain:
            domain = self.default_domain
        return await self.count_by_filter(domain)

    async def new(self, data={}, rec_name="", trnf_config={}) -> CoreModel:
        if not self.chk_write_permission():
            msg = _("Session is Readonly")
            self.error_status(msg, data={})
            return None
        if not self.chk_write_permission():
            raise SessionException(detail="Session is Readonly")
        if not data and rec_name or rec_name and self.virtual:
            if not self.is_session_model:
                data["rec_name"] = rec_name
        if not self.virtual:
            data = self._make_from_dict(copy.deepcopy(data))
        self.transform_config = trnf_config.copy()
        self.load_data(data)
        if not self.name_allowed.match(self.modelr.rec_name):
            msg = (
                _("Not allowed chars in field name: %s") % self.modelr.rec_name
            )
            self.error_status(msg, data=data)
            return None
        self.modelr.set_active()

        return self.modelr

    async def insert(self, record: CoreModel) -> CoreModel:
        self.init_status()
        if not self.chk_write_permission():
            msg = _("Session is Readonly")
            self.error_status(msg, data={})
            return None
        if self.virtual and not self.data_model:
            self.error_status(
                _("Cannot save on db a virtual object"),
                record.get_dict_copy(),
            )
            return None
        try:
            if not record.rec_name or not self.name_allowed.match(
                record.rec_name
            ):
                msg = _("Not allowed chars in field name: %s") % record.get(
                    "rec_name"
                )
                self.error_status(msg, data=record.get_dict_json())
                return None

            coll = self.db.engine.get_collection(self.data_model)

            record.create_datetime = datetime.now().isoformat()
            record = self.set_user_data(record, self.user_session)
            record.list_order = await self.count()
            record.active = True
            to_save = self._make_from_dict(copy.deepcopy(record.get_dict()))
            if "_id" not in to_save:
                to_save['_id'] = bson.ObjectId(to_save['id'])
            result_save = await coll.insert_one(to_save)
            result = None
            if result_save:
                return await self.load({"rec_name": to_save['rec_name']})
            return result
        except pymongo.errors.DuplicateKeyError as e:
            logger.error(f" Duplicate {e.details['errmsg']}")
            field = e.details["keyValue"]
            key = list(field.keys())[0]
            val = field[key]
            self.error_status(
                _("Duplicate key error %s: %s") % (str(key), str(val)),
                record.get_dict_copy(),
            )
            return None
        except pydantic.ValidationError as e:
            logger.error(f" Validation {e}")
            self.error_status(
                _("Validation Error  %s ") % str(e), record.get_dict_copy()
            )
            return None

    async def copy(self, domain) -> CoreModel:
        self.init_status()
        if not self.chk_write_permission():
            msg = _("Session is Readonly")
            self.error_status(msg, data={})
            return None
        if self.is_session_model or self.virtual:
            self.error_status(
                _(
                    "Duplicate session instance "
                    "or virtual model is not allowed"
                ),
                domain,
            )
            return None
        record_to_copy = await self.load(domain)
        self.modelr.renew_id()
        if (
            hasattr(record_to_copy, "rec_name")
            and self.name not in record_to_copy.rec_name
        ):
            self.modelr.rec_name = f"{self.modelr.rec_name}_copy"
        else:
            self.modelr.rec_name = f"{self.data_model}.{self.modelr.id}"
        self.modelr.list_order = await self.count()
        self.modelr.create_datetime = datetime.now().isoformat()
        self.modelr.update_datetime = datetime.now().isoformat()
        record = await self.new(data=self.modelr.get_dict())
        record = self.set_user_data(record, self.user_session)
        for k in self.model.get_unique_fields():
            if k not in ["rec_name"]:
                record.set(k, f"{record.get(k)}_copy")
        record.set_active()
        return record

    async def update(self, record: CoreModel, remove_mata=True) -> CoreModel:
        self.init_status()
        if not self.chk_write_permission():
            msg = _("Session is Readonly")
            self.error_status(msg, data=record.get_dict_json())
            return None
        if self.virtual and not self.data_model:
            self.error_status(
                _("Cannot update a virtual object"), record.get_dict_copy()
            )
            return None
        try:
            coll = self.db.engine.get_collection(self.data_model)
            original = await self.load(record.rec_name_domain())
            if not self.virtual:
                to_save = original.get_dict_diff(
                    record.get_dict_copy(),
                    ignore_fields=default_list_metadata_fields_update,
                    remove_ignore_fileds=remove_mata,
                )

            else:
                to_save = self._make_from_dict(
                    copy.deepcopy(record.get_dict())
                )
            if "rec_name" in to_save:
                to_save.pop("rec_name")
            to_save["update_uid"] = self.orm.user_session.get("user.uid")
            to_save["update_datetime"] = datetime.now().isoformat()
            await coll.update_one(record.rec_name_domain(), {"$set": to_save})
            return await self.load(record.rec_name_domain())
        except pymongo.errors.DuplicateKeyError as e:
            logger.error(f" Duplicate {e.details['errmsg']}")
            field = e.details["keyValue"]
            key = list(field.keys())[0]
            val = field[key]
            self.error_status(
                _("Duplicate key error %s: %s") % (str(key), str(val)),
                record.get_dict_copy(),
            )
            return None
        except pydantic.ValidationError as e:
            logger.error(f" Validation {e}")
            self.error_status(
                _("Validation Error  %s ") % str(e),
                record.get_dict_copy(),
            )
            return None

    async def remove(self, record: CoreModel) -> bool:
        self.init_status()
        if not self.chk_write_permission():
            msg = _("Session is Readonly")
            self.error_status(msg, data=record.get_dict_json())
            return None
        if self.virtual and not self.data_model:
            self.error_status(
                _("Cannot delete a virtual object"), record.get_dict_copy()
            )
            return False
        coll = self.db.engine.get_collection(self.data_model)
        await coll.delete_one(record.rec_name_domain())
        return True

    async def remove_all(self, domain) -> int:
        self.init_status()
        if not self.chk_write_permission():
            msg = _("Session is Readonly")
            self.error_status(msg, data={})
            return None
        if self.virtual and not self.data_model:
            msg = _(
                "Data Model is required for virtual model to get data from db"
            )
            self.error_status(msg, domain)
            return 0
        coll = self.db.engine.get_collection(self.data_model)
        num = await coll.delete_many(domain)
        return num

    async def load(self, domain: dict) -> CoreModel:
        data = await self.load_raw(domain)
        if self.status.fail:
            return None
        self.load_data(data)
        return self.modelr

    async def load_raw(self, domain: dict) -> dict:
        self.init_status()
        if self.virtual and not self.data_model:
            msg = _(
                "Data Model is required for virtual model to get data from db"
            )
            self.error_status(msg, data=domain)
            return None
        coll = self.db.engine.get_collection(self.data_model)
        data = await coll.find_one(domain)

        if not data:
            self.error_status(_("Not found"), domain)
            return {}
        if data.get("_id"):
            data.pop("_id")
        return data

    async def find(
        self, domain: dict, sort: str = "", limit=0, skip=0, pipeline_items=[]
    ) -> list[CoreModel]:
        datas = await self.find_raw(
            domain,
            sort=sort,
            limit=limit,
            skip=skip,
            pipeline_items=pipeline_items,
            fields={},
        )
        res = []
        if datas:
            for rec_dat in datas:
                rec_data = json.loads(json.dumps(rec_dat, cls=JsonEncoder))
                if "_id" in rec_data:
                    rec_data['id'] = rec_data.pop("_id")
                if self.virtual:
                    res.append(self.load_data(rec_data))
                else:
                    res.append(self.model(**rec_data))
        return res

    async def find_raw(
        self,
        domain: dict,
        sort: str = "",
        limit=0,
        skip=0,
        pipeline_items=[],
        fields={},
    ) -> list[dict]:
        self.init_status()
        if self.virtual and not self.data_model:
            msg = _(
                "Data Model is required for virtual model to get data from db"
            )
            self.error_status(msg, domain)
            return []
        _sort = self.eval_sort_str(sort)
        coll = self.db.engine.get_collection(self.data_model)
        if fields and not pipeline_items:
            res = []
            if limit > 0:
                datas = (
                    coll.find(domain, projection=fields)
                    .sort(sort)
                    .skip(skip)
                    .limit(limit)
                )
            elif sort:
                datas = coll.find(domain, projection=fields).sort(sort)
            else:
                datas = coll.find(domain, projection=fields)
            if datas:
                return await datas.to_list(length=None)
        else:
            res = []
            pipeline = [{"$match": domain}]
            for item in pipeline_items:
                pipeline.append(item)
            if _sort:
                pipeline.append({"$sort": _sort})
            if limit > 0:
                pipeline.append({"$skip": skip})
                pipeline.append({"$limit": limit})
            datas = coll.aggregate(pipeline)
            if datas:
                return await datas.to_list(length=None)

        return res

    async def aggregate_raw(
        self, pipeline: list, sort: str = "", limit=0, skip=0
    ) -> list[Any]:
        if sort:
            _sort = self.eval_sort_str(sort)
            pipeline.append({"$sort": _sort})
        if limit > 0:
            pipeline.append({"$skip": skip})
            pipeline.append({"$limit": limit})
        coll = self.db.engine.get_collection(self.data_model)
        datas = await coll.aggregate(pipeline).to_list(length=None)
        return datas

    async def aggregate(
        self, pipeline: list, sort: str = "", limit=0, skip=0
    ) -> list[CoreModel]:
        datas = await self.aggregate_raw(
            pipeline, sort=sort, limit=limit, skip=skip
        )
        res = []
        for rec_dat in datas:
            rec_data = json.loads(json.dumps(rec_dat, cls=JsonEncoder))
            agg_mm = ModelMaker(f"{self.data_model}.agg")
            if "_id" in rec_data:
                rec_data['id'] = rec_data.pop("_id")
            agg_mm.from_data_dict(rec_data)
            agg_mm.new(),
            res.append(agg_mm.instance)
        return res

    async def distinct(self, field_name: str, query: dict) -> list[Any]:
        self.init_status()
        if self.virtual and not self.data_model:
            msg = _(
                "Data Model is required for virtual model to get data from db"
            )
            self.error_status(msg, query)
            return []
        coll = self.db.engine.get_collection(self.data_model)
        datas = await coll.distinct(field_name, query)
        return datas

    async def search_all_distinct(
        self,
        distinct="",
        query: dict = {},
        compute_label="",
        sort: str = "",
        limit=0,
        skip=0,
        raw_result=False,
    ) -> list[Any]:
        self.init_status()
        if self.virtual and not self.data_model:
            msg = _(
                "Data Model is required for virtual model to get data from db"
            )
            self.error_status(msg, query)
            return []
        if not query:
            query = {"deleted": 0}
        label = {"$first": "$title"}
        label_lst = compute_label.split(",")
        project = {
            distinct: {"$toString": f"${distinct}"},
            "type": {"$toString": "$type"},
        }
        if compute_label:
            if len(label_lst) > 0:
                block = []
                for item in label_lst:
                    if len(block) > 0:
                        block.append(" - ")
                    block.append(f"${item}")
                    project.update({item: {"$toString": f"${item}"}})
                label = {"$first": {"$concat": block}}

            else:
                project.update(
                    {label_lst[0]: {"$toString": f"${label_lst[0]}"}}
                )
                label = {"$first": f"${label_lst[0]}"}
        else:
            project.update({"title": 1})

        pipeline = [
            {"$match": query},
            {"$project": project},
            {
                "$group": {
                    "_id": "$_id",
                    f"{distinct}": {"$first": f"${distinct}"},
                    "title": label,
                    "type": {"$first": "$type"},
                }
            },
        ]
        if raw_result:
            return await self.aggregate_raw(
                pipeline, sort=sort, limit=limit, skip=skip
            )
        else:
            return await self.aggregate(
                pipeline, sort=sort, limit=limit, skip=skip
            )

    async def set_to_delete(self, record: CoreModel) -> CoreModel:
        self.init_status()
        if not self.chk_write_permission():
            msg = _("Session is Readonly")
            self.error_status(msg, data=record.get_dict_json())
            return None
        if self.virtual:
            msg = _("Unable to set to delete a virtual model")
            self.error_status(msg, record.get_dict_copy())
            return False
        delete_at_datetime = datetime.now() + timedelta(
            days=self.setting_app.delete_record_after_days
        )
        record.set_to_delete(delete_at_datetime.timestamp())
        return await self.update(record)

    async def set_active(self, record: CoreModel) -> CoreModel:
        self.init_status()
        if not self.chk_write_permission():
            msg = _("Session is Readonly")
            self.error_status(msg, data=record.get_dict_json())
            return None
        if self.virtual:
            msg = _("Unable to set to delete a virtual model")
            self.error_status(msg, record.get_dict_copy())
            return False
        record.set_active()
        await self.update(record)
        return record
