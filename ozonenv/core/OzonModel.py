import json
from datetime import datetime, timedelta
from ModelMaker import ModelMaker
from pydantic.main import ModelMetaclass
from BaseModels import (
    Component,
    BasicModel,
    CoreModel,
    default_list_metadata_fields_update,
)
import re
import copy
import bson
import logging

import pydantic
import pymongo
from i18n import _

logger = logging.getLogger("asyncio")


class OzonModelBase:
    #
    def __init__(
        self,
        model_name,
        session_model=False,
        virtual=False,
        static: BasicModel = None,
        schema={},
    ):
        self.name = model_name
        self.virtual = virtual
        self.static: BasicModel = static
        self.model_meta: ModelMetaclass = None
        self.schema = copy.deepcopy(schema)
        self.schema_object: CoreModel = None
        self._default_domain = {"active": True, "deleted": 0}
        self.is_session_model = session_model
        self.model_record: CoreModel = None
        self.mm: ModelMaker = None
        self.name_allowed = re.compile(r"^[A-Za-z0-9._~()'!*:@,;+?-]*$")
        self.sort_dir = {"asc": 1, "desc": -1}
        self.default_sort_str = "list_order:desc,"
        self.sort_rule = []
        self.init_model()

    @property
    def unique_fields(self):
        return self.mm.unique_fields

    @property
    def user_session(self):
        return self.orm.user_session

    def init_model(self):
        self.mm = ModelMaker(self.name)
        if self.static:
            self.mm.model = self.static
            self.model_meta = self.static
            for field in self.static.get_unique_fields():
                if field not in self.mm.unique_fields:
                    self.mm.unique_fields.append(field)

        elif not self.static and not self.virtual:
            c_maker = ModelMaker("component")
            c_maker.model = Component
            c_maker.new()
            self.schema_object = c_maker.instance
            self.model_meta = self.mm.from_formio(self.schema)
            if self.schema_object.properties.get("sort", False):
                self.default_sort_str = self.schema_object.properties.get(
                    "sort"
                )

    def eval_sort_str(self, sortstr="") -> list[tuple]:
        """
        eval sort string in sort rule
        :param sortstr: eg. list_order:asc,rec_name:desc
        :return: List(Tuple) eg. [('list_order', 1),('rec_name', -1)]
        """
        if not sortstr:
            sortstr = self.default_sort_str
        sort_rules = sortstr.split(",")
        sort = []
        for rule_str in sort_rules:
            if rule_str:
                rule_list = rule_str.split(":")
                if len(rule_list) > 1:
                    rule = (rule_list[0], self.sort_dir[rule_list[1]])
                    sort.append(rule)
        return sort

    async def set_lang(self):
        self.lang = self.orm.lang

    async def init_unique(self):
        for field in self.mm.unique_fields:
            await self.set_unique(field)

    async def set_unique(self, field_name):
        component_coll = self.db.engine.get_collection(self.name)
        await component_coll.create_index([(field_name, 1)], unique=True)

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

    def _make_from_dict(self, dict_data, root_dict=None):
        res_dict = {}
        for k, v in dict_data.items():
            if isinstance(v, dict):  # For DICT
                res_dict[k] = self._make_from_dict(v)
            elif isinstance(v, list):  # For LIST
                res_dict[k] = [
                    self._make_from_dict(i) for i in v if isinstance(i, dict)
                ]
            else:
                # Update Key-Value fields
                # TODO handle all key-value fields and resources
                # TODO check if resource only for non virtual
                if self._value_type(v) is datetime:
                    if "data_value" not in res_dict:
                        res_dict["data_value"] = {}
                    res_dict["data_value"][k] = self.env.readable_datetime(v)
                res_dict[k] = v

        return res_dict.copy()

    def _load_data(self, data):
        if not self.virtual:
            self.mm.new(data)
        else:
            self.mm.from_data_dict(data)
            self.mm.new()
        self.model_record = self.mm.instance
        if not self.is_session_model and not self.model_record.rec_name:
            self.model_record.rec_name = f"{self.name}.{self.model_record.id}"

    def error_response(self, msg, data) -> CoreModel:
        return CoreModel(
            **{"status": "error", "message": msg, "res_data": data}
        )

    async def count_by_filter(self, domain: dict) -> int:
        coll = self.db.engine.get_collection(self.name)
        val = await coll.count_documents(domain)
        if not val:
            val = 0
        return int(val)

    async def count(self, domain={}) -> int:
        if not self.virtual:
            if not domain:
                domain = self._default_domain
            return await self.count_by_filter(domain)
        else:
            return 0

    async def new(
        self,
        data={},
        rec_name="",
    ) -> CoreModel:

        if not data and rec_name or rec_name and self.virtual:
            if not self.is_session_model:
                data["rec_name"] = rec_name

        if not self.name_allowed.match(data["rec_name"]):
            msg = _("Not allowed chars in field name: %s") % data["rec_name"]
            return self.error_response(msg, data=data)
        if not self.virtual:
            data = self._make_from_dict(copy.deepcopy(data))
        self._load_data(data)

        self.model_record.set_active()
        return self.model_record

    def set_user_data(self, record: CoreModel) -> CoreModel:
        record.owner_uid = self.orm.user_session.get("user.uid")
        record.owner_name = self.orm.user_session.get("user.full_name", "")
        record.owner_mail = self.orm.user_session.get("user.mail", "")
        record.owner_sector = self.orm.user_session.get("sector", "")
        record.owner_sector_id = self.orm.user_session.get("sector_id", "")
        record.owner_personal_type = self.orm.user_session.get(
            "user.tipo_personale", ""
        )
        record.owner_job_title = self.orm.user_session.get(
            "user.qualifica", ""
        )
        record.owner_function = self.orm.user_session.get("function", "")
        return record

    async def insert(self, record: CoreModel) -> CoreModel:
        if self.virtual:
            return self.error_response(
                _("Cannot save on db a virtual object"),
                record.get_dict_copy(),
            )
        try:
            if not self.name_allowed.match(record.get("rec_name")):
                msg = _("Not allowed chars in field name: %s") % record.get(
                    "rec_name"
                )
                return self.error_response(msg, data=record.get_dict_copy())
            coll = self.db.engine.get_collection(self.name)
            record.list_order = await self.count()
            record.create_datetime = datetime.now()
            record = self.set_user_data(record)
            result_save = await coll.insert_one(record.get_dict_copy())
            result = None
            if result_save:
                return await self.load(
                    {"_id": bson.ObjectId(result_save.inserted_id)}
                )
            return result
        except pymongo.errors.DuplicateKeyError as e:
            logger.error(f" Duplicate {e.details['errmsg']}")
            field = e.details["keyValue"]
            key = list(field.keys())[0]
            val = field[key]
            return self.error_response(
                _("Duplicate key error %s: %s") % (str(key), str(val)),
                record.get_dict_copy(),
            )
        except pydantic.error_wrappers.ValidationError as e:
            logger.error(f" Validation {e}")
            return self.error_response(
                _("Validation Error  %s ") % str(e), record.get_dict_copy()
            )

    async def copy(self, domain) -> CoreModel:
        if self.is_session_model:
            return self.error_response(
                _("Duplicate session instance is not allowed"), domain
            )
        record_to_copy = await self.load(domain)
        self.model_record.renew_id()
        if (
            hasattr(record_to_copy, "rec_name")
            and self.name not in record_to_copy.rec_name
        ):
            self.model_record.rec_name = f"{self.model_record.rec_name}_copy"
        else:
            self.model_record.rec_name = f"{self.name}.{self.model_record.id}"
        self.model_record.list_order = await self.count()
        self.model_record.create_datetime = datetime.now()
        self.model_record.update_datetime = datetime.now()
        record = await self.new(data=self.model_record.get_dict())
        record = self.set_user_data(record)
        for k in self.mm.unique_fields:
            if k not in ["rec_name"]:
                record.set(k, f"{record.get(k)}_copy")
        record.set_active()
        return record

    async def update(self, record: CoreModel) -> CoreModel:
        if self.virtual:
            return self.error_response(
                _("Cannot update a virtual object"), record.get_dict_copy()
            )
        try:
            coll = self.db.engine.get_collection(self.name)
            original = await self.load(record.rec_name_domain())
            to_save = original.get_dict_diff(
                record.get_dict_copy(),
                default_list_metadata_fields_update,
                True,
            )
            if "rec_name" in to_save:
                to_save.pop("rec_name")
            to_save["update_uid"] = self.orm.user_session.get("user.uid")
            to_save["update_datetime"] = datetime.now()
            print(to_save)
            await coll.update_one(record.rec_name_domain(), {"$set": to_save})
            return await self.load(record.rec_name_domain())
        except pymongo.errors.DuplicateKeyError as e:
            logger.error(f" Duplicate {e.details['errmsg']}")
            field = e.details["keyValue"]
            key = list(field.keys())[0]
            val = field[key]
            return self.error_response(
                _("Duplicate key error %s: %s") % (str(key), str(val)),
                record.get_dict_copy(),
            )
        except pydantic.error_wrappers.ValidationError as e:
            logger.error(f" Validation {e}")
            return self.error_response(
                _("Validation Error  %s ") % str(e),
                record.get_dict_copy(),
            )

    async def remove(self, record: CoreModel):
        coll = self.db.engine.get_collection(self.name)
        await coll.delete_one(record.rec_name_domain())
        return True

    async def remove_all(self, domain) -> int:
        coll = self.db.engine.get_collection(self.name)
        num = await coll.delete_many(domain)
        return num

    async def load(self, domain: dict) -> CoreModel:
        coll = self.db.engine.get_collection(self.name)
        data = await coll.find_one(domain)
        if not data:
            return self.error_response(_("Not found"), domain)
        self._load_data(data)
        return self.model_record

    async def find(
        self, domain: dict, sort: str = "", limit=0, skip=0
    ) -> list[CoreModel]:
        _sort = self.eval_sort_str(sort)
        coll = self.db.engine.get_collection(self.name)
        res = []
        if limit > 0:
            datas = coll.find(domain).sort(_sort).skip(skip).limit(limit)
        elif sort:
            datas = coll.find(domain).sort(_sort)
        else:
            datas = coll.find(domain)
        if datas:
            res = []
            for rec_data in await datas.to_list(length=None):
                self.mm.new(rec_data)
                res.append(self.mm.instance)
        return res

    async def aggregate(
        self, pipeline: list, sort: str, limit=0, skip=0
    ) -> list[CoreModel]:
        _sort = self.eval_sort_str(sort)
        coll = self.db.engine.get_collection(self.name)
        if _sort:
            s = {"$sort": {}}
            for item in _sort:
                s["$sort"][item[0]] = item[1]
            pipeline.append(s)
        if skip:
            pipeline.append({"$skip": skip})
        if limit:
            pipeline.append({"$limit": limit})

        datas = await coll.aggregate(pipeline).to_list(None)
        res = []

        agg_mm = ModelMaker(f"{self.name}.agg")
        for rec_data in datas:
            if "_id" in rec_data:
                rec_data.pop("_id")
            agg_mm.from_data_dict(rec_data)
            agg_mm.new(),
            res.append(agg_mm.instance)
        return res

    async def search_all_distinct(
        self,
        distinct="",
        query={},
        compute_label="",
        sort: str = "",
        limit=0,
        skip=0,
    ) -> list[CoreModel]:
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
        return await self.aggregate(
            pipeline, sort=sort, limit=limit, skip=skip
        )

    async def set_to_delete(self, record: CoreModel) -> CoreModel:
        delete_at_datetime = datetime.now() + timedelta(
            days=self.env.config_system["delete_record_after_days"]
        )
        record.set_to_delete(delete_at_datetime.timestamp())
        return record
