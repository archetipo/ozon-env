from datetime import datetime, timedelta
from pydantic.main import ModelMetaclass
from ozonenv.core.ModelMaker import ModelMaker
from ozonenv.core.BaseModels import default_list_metadata
from ozonenv.core.BaseModels import (
    Component,
    DictRecord,
    BasicModel,
    CoreModel,
    BasicReturn,
    default_list_metadata_clean,
)
from ozonenv.core.i18n import _
import re
import copy
import bson
import logging

import pydantic
import pymongo

logger = logging.getLogger(__file__)


class OzonModelBase:
    def __init__(
        self,
        model_name,
        data_model="",
        session_model=False,
        virtual=False,
        static: BasicModel = None,
        schema={},
    ):
        self.name = model_name
        self.virtual = virtual
        self.static: BasicModel = static
        if self.virtual:
            self.data_model = data_model
        else:
            self.data_model = data_model or model_name
        self.model_meta: ModelMetaclass = None
        self.schema = copy.deepcopy(schema)
        self.schema_object: CoreModel = None
        self.default_domain = {"active": True, "deleted": 0}
        self.is_session_model = session_model
        self.model_record: CoreModel = None
        self.mm: ModelMaker = None
        self.name_allowed = re.compile(r"^[A-Za-z0-9._~()'!*:@,;+?-]*$")
        self.sort_dir = {"asc": 1, "desc": -1}
        self.default_sort_str = "list_order:desc,"
        self.sort_rule = []
        self.status: BasicReturn = BasicReturn(
            **{"fail": False, "msg": "", "data": {}}
        )
        self.transform_config = {}
        self.init_model()

    @property
    def unique_fields(self):
        return self.mm.unique_fields

    @property
    def user_session(self):
        return self.orm.user_session

    @property
    def message(self):
        return self.status.msg

    def is_error(self):
        return self.status.fail

    def get_domain(self, domain={}):
        _domain = self.default_domain.copy()
        _domain.update(domain)
        return _domain

    def init_model(self):
        self.init_status()
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
        self.init_status()
        component_coll = self.db.engine.get_collection(self.data_model)
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
                if "data_value" not in res_dict:
                    res_dict["data_value"] = {}
                if k in self.mm.tranform_data_value:
                    res_dict["data_value"][k] = self.env.make_data_value(
                        v, self.mm.tranform_data_value[k]
                    )
                elif self._value_type(v) is datetime:
                    res_dict["data_value"][k] = self.env.make_data_value(
                        v, {"type": datetime}
                    )
                elif self._value_type(v) is float:
                    res_dict["data_value"][k] = self.env.make_data_value(
                        v, {"type": float, "dp": 2}
                    )
                res_dict[k] = v

        return res_dict.copy()

    def _load_data(self, data):
        if not self.virtual:
            self.mm.new(data)
        else:
            self.mm = ModelMaker(self.data_model)
            if self.transform_config:
                self.mm.tranform_data_value = self.transform_config.copy()
            if data.get("_id"):
                data.pop("_id")
            self.mm.from_data_dict(data)
            self.mm.new()
        self.model_record = self.mm.instance
        if not self.is_session_model and not self.model_record.rec_name:
            self.model_record.rec_name = (
                f"{self.data_model}.{self.model_record.id}"
            )

    def error_status(self, msg, data):
        self.status.fail = True
        self.status.msg = msg
        self.status.data = data

    def init_status(self):
        self.status.fail = False
        self.status.msg = ""
        self.status.data = {}

    async def count_by_filter(self, domain: dict) -> int:
        self.init_status()
        coll = self.db.engine.get_collection(self.data_model)
        val = await coll.count_documents(domain)
        if not val:
            val = 0
        return int(val)

    async def count(self, domain={}) -> int:
        self.init_status()
        if not self.virtual or self.data_model:
            if not domain:
                domain = self.default_domain
            return await self.count_by_filter(domain)
        else:
            return 0

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

    async def new(self, data={}, rec_name="", trnf_config={}) -> CoreModel:
        self.init_status()
        if not data and rec_name or rec_name and self.virtual:
            if not self.is_session_model:
                data["rec_name"] = rec_name
        if not self.virtual:
            data = self._make_from_dict(copy.deepcopy(data))
        self.transform_config = trnf_config.copy()
        self._load_data(data)
        if not self.name_allowed.match(self.model_record.rec_name):
            msg = (
                _("Not allowed chars in field name: %s")
                % self.model_record.rec_name
            )
            self.error_status(msg, data=data)
            return None
        self.model_record.set_active()

        return self.model_record

    def set_user_data(self, record: CoreModel, user={}) -> CoreModel:
        record.owner_uid = user.get("user.uid")
        record.owner_name = user.get("user.full_name", "")
        record.owner_mail = user.get("user.mail", "")
        record.owner_sector = user.get("sector", "")
        record.owner_sector_id = user.get("sector_id", "")
        record.owner_personal_type = user.get("user.tipo_personale", "")
        record.owner_job_title = user.get("user.qualifica", "")
        record.owner_function = user.get("function", "")
        return record

    async def insert(self, record: CoreModel) -> CoreModel:
        self.init_status()
        if self.virtual and not self.data_model:
            self.error_status(
                _("Cannot save on db a virtual object"),
                record.get_dict_copy(),
            )
            return None
        try:
            if not self.name_allowed.match(record.rec_name):
                msg = _("Not allowed chars in field name: %s") % record.get(
                    "rec_name"
                )
                self.error_status(msg, data=record.get_dict_json())
                return None

            coll = self.db.engine.get_collection(self.data_model)
            record.list_order = await self.count()
            record.create_datetime = datetime.now().isoformat()
            record = self.set_user_data(record, self.user_session)
            to_save = self._make_from_dict(copy.deepcopy(record.get_dict()))
            result_save = await coll.insert_one(to_save)
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
            self.error_status(
                _("Duplicate key error %s: %s") % (str(key), str(val)),
                record.get_dict_copy(),
            )
            return None
        except pydantic.error_wrappers.ValidationError as e:
            logger.error(f" Validation {e}")
            self.error_status(
                _("Validation Error  %s ") % str(e), record.get_dict_copy()
            )
            return None

    async def copy(self, domain) -> CoreModel:
        self.init_status()
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
        self.model_record.renew_id()
        if (
            hasattr(record_to_copy, "rec_name")
            and self.name not in record_to_copy.rec_name
        ):
            self.model_record.rec_name = f"{self.model_record.rec_name}_copy"
        else:
            self.model_record.rec_name = (
                f"{self.data_model}.{self.model_record.id}"
            )
        self.model_record.list_order = await self.count()
        self.model_record.create_datetime = datetime.now().isoformat()
        self.model_record.update_datetime = datetime.now().isoformat()
        record = await self.new(data=self.model_record.get_dict())
        record = self.set_user_data(record, self.user_session)
        for k in self.mm.unique_fields:
            if k not in ["rec_name"]:
                record.set(k, f"{record.get(k)}_copy")
        record.set_active()
        return record

    async def update(self, record: CoreModel) -> CoreModel:
        self.init_status()
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
                    default_list_metadata_clean,
                    True,
                )
            else:
                record.list_order = await self.count()
                to_save = self._make_from_dict(
                    copy.deepcopy(record.get_dict())
                )
            if "rec_name" in to_save:
                to_save.pop("rec_name")
            to_save["active"] = True
            to_save["deleted"] = 0
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
        except pydantic.error_wrappers.ValidationError as e:
            logger.error(f" Validation {e}")
            self.error_status(
                _("Validation Error  %s ") % str(e),
                record.get_dict_copy(),
            )
            return None

    async def remove(self, record: CoreModel) -> bool:
        if self.virtual and not self.data_model:
            self.error_status(
                _("Cannot delete a virtual object"), record.get_dict_copy()
            )
            return False
        coll = self.db.engine.get_collection(self.data_model)
        await coll.delete_one(record.rec_name_domain())
        return True

    async def remove_all(self, domain) -> int:
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
            return None

        self._load_data(data)

        return self.model_record

    async def find(
        self, domain: dict, sort: str = "", limit=0, skip=0
    ) -> list[CoreModel]:
        self.init_status()
        if self.virtual and not self.data_model:
            msg = _(
                "Data Model is required for virtual model to get data from db"
            )
            self.error_status(msg, domain)
            return []
        _sort = self.eval_sort_str(sort)
        coll = self.db.engine.get_collection(self.data_model)
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

        self.init_status()
        if self.virtual and not self.data_model:
            msg = _(
                "Data Model is required for virtual model to get data from db"
            )
            self.error_status(msg, pipeline)
            return []
        _sort = self.eval_sort_str(sort)
        coll = self.db.engine.get_collection(self.data_model)
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

        agg_mm = ModelMaker(f"{self.data_model}.agg")
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
        return await self.aggregate(
            pipeline, sort=sort, limit=limit, skip=skip
        )

    async def set_to_delete(self, record: CoreModel) -> bool:
        self.init_status()
        if self.virtual:
            msg = _("Unable to set to delete a virtual model")
            self.error_status(msg, record.get_dict_copy())
            return False
        delete_at_datetime = datetime.now() + timedelta(
            days=self.env.config_system["delete_record_after_days"]
        )
        record.set_to_delete(delete_at_datetime.timestamp())
        await self.update(record)
        return True
