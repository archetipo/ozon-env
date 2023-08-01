# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from __future__ import annotations

import copy
import json
import logging
import operator
import re
from datetime import datetime
from functools import reduce
from typing import List, Optional, Dict
from typing import TypeVar

# from datetime import datetime
from dateutil.parser import parse
from pydantic import BaseModel, Field, field_serializer

import ozonenv
from ozonenv.core.db.BsonTypes import BSON_TYPES_ENCODERS, PyObjectId, bson

logger = logging.getLogger("asyncio")

T = TypeVar("T", bound=BaseModel)
ModelType = TypeVar("ModelType", bound=BaseModel)

default_fields = [
    "owner_uid",
    "owner_name",
    "owner_function",
    "owner_sector",
    "create_datetime",
    "update_uid",
    "update_datetime",
    "owner_personal_type",
    "owner_job_title",
    "owner_function_type",
    "owner_mail",
]

list_default_fields_update = [
    "create_datetime",
    "update_uid",
    "update_datetime",
]

data_fields = ["data", "data_value"]

default_data_fields = default_fields + data_fields

default_data_fields_update = list_default_fields_update + data_fields

default_list_metadata = [
    "id",
    "rec_name",
    "owner_uid",
    "owner_name",
    "owner_sector",
    "owner_sector_id",
    "owner_function",
    "update_datetime",
    "create_datetime",
    "owner_mail",
    "owner_function_type",
    "childs",
    "update_uid",
    "app_code",
    "parent",
    "process_id",
    "data_value",
    "sys",
    "demo",
    "deleted",
    "list_order",
    "owner_personal_type",
    "owner_job_title",
]
default_list_metadata_clean = [
    "id",
    "rec_name",
    "owner_uid",
    "owner_name",
    "owner_sector",
    "owner_sector_id",
    "owner_function",
    "update_datetime",
    "create_datetime",
    "owner_mail",
    "owner_function_type",
    "childs",
    "update_uid",
    "app_code",
    "parent",
    "process_id",
    "sys",
    "demo",
    "deleted",
    "list_order",
    "owner_personal_type",
    "owner_job_title",
]

default_list_metadata_fields = [
    "id",
    "owner_uid",
    "owner_name",
    "owner_sector",
    "owner_sector_id",
    "owner_function",
    "update_datetime",
    "create_datetime",
    "owner_mail",
    "update_uid",
    "owner_function_type",
    "sys",
    "demo",
    "deleted",
    "list_order",
    "owner_personal_type",
    "owner_job_title",
]

default_list_metadata_fields_update = [
    "id",
    "rec_name",
    "owner_uid",
    "owner_name",
    "owner_sector",
    "owner_sector_id",
    "owner_function",
    "create_datetime",
    "owner_mail",
    "owner_personal_type",
    "owner_job_title",
]

export_list_metadata = [
    "owner_uid",
    "owner_name",
    "owner_function",
    "owner_sector",
    "owner_sector_id",
    "owner_personal_type",
    "owner_job_title",
    "owner_function_type",
    "create_datetime",
    "update_uid",
    "update_datetime",
    "list_order",
    "owner_mail",
    "sys",
]


class DbViewModel(BaseModel):
    name: str
    model: str
    force_recreate: bool = False
    pipeline: list


class MainModel(BaseModel):
    @classmethod
    def str_name(cls, *args, **kwargs):
        return cls.model_json_schema(*args, **kwargs).get("title", "").lower()

    def get_dict(self, exclude=[]):
        basic = ["status", "message", "res_data"]
        # d = json.loads(self.json(exclude=set().union(basic, exclude)))
        d = self.model_copy(deep=True).model_dump(
            exclude=set().union(basic, exclude)
        )
        return d

    def get_dict_json(self, exclude=[]):
        basic = ["status", "message", "res_data"]
        return json.loads(
            self.model_dump_json(exclude=set().union(basic, exclude))
        )

    def get_dict_copy(self):
        return copy.deepcopy(self.get_dict())

    def get_dict_diff(
        self, to_compare_dict, ignore_fields=[], remove_ignore_fileds=True
    ):
        if ignore_fields and remove_ignore_fileds:
            original_dict = self.get_dict(exclude=ignore_fields)
        else:
            original_dict = self.get_dict()
        diff = {
            k: v
            for k, v in to_compare_dict.items()
            if k in original_dict and not original_dict[k] == v
        }
        return diff.copy()

    def scan_data(self, key, default=None):
        data = self.get_dict(exclude=["_id", "id"])
        try:
            _keys = key.split(".")
            keys = []
            for v in _keys:
                if str(v).isdigit():
                    keys.append(int(v))
                else:
                    keys.append(v)
            lastplace = reduce(operator.getitem, keys[:-1], dict(data))
            return lastplace.get(keys[-1], default)
        except Exception as e:
            print(f" error scan_data {e} field not foud")
            return default

    def get(self, val, default: Optional = None):
        if "." in val:
            return self.scan_data(val, default)
        elif default:
            return getattr(self, val, default)
        else:
            return getattr(self, val)

    def set_from_child(self, key, nodes: str, default):
        setattr(self, key, self.get(nodes, default))

    def set(self, key, value):
        setattr(self, key, value)

    def set_many(self, data_dict):
        for k, v in data_dict.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def selection_value(self, key, value, read_value):
        setattr(self, key, value)
        self.data_value[key] = read_value

    def selection_value_from_record(self, key, src, src_key=""):
        if not src_key:
            src_key = key
        setattr(self, key, getattr(src, src_key))
        self.data_value[key] = src.data_value[src_key]

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": BSON_TYPES_ENCODERS,
    }


class CoreModel(MainModel):
    id: PyObjectId = Field(
        default_factory=ozonenv.core.db.BsonTypes.PyObjectId, alias="_id"
    )
    data_model: str = ""
    rec_name: str = ""
    app_code: List = Field(default=[])
    parent: str = ""
    process_id: str = ""
    process_task_id: str = ""
    data_value: dict = {}
    owner_name: str = ""
    deleted: float = 0
    list_order: int = 0
    owner_uid: str = ""
    owner_mail: str = ""
    owner_function: str = ""
    owner_function_type: str = ""
    owner_sector: str = ""
    owner_sector_id: int = 0
    owner_personal_type: str = ""
    owner_job_title: str = ""
    update_uid: str = ""
    sys: bool = False
    default: bool = False
    active: bool = True
    demo: bool = False
    childs: List[Dict] = Field(default=[])
    create_datetime: datetime = Field(default="1970-01-01T00:00:00")
    update_datetime: datetime = Field(default="1970-01-01T00:00:00")
    status: str = "ok"
    message: str = ""
    res_data: dict = Field(default={})

    @field_serializer('id')
    def serialize_dt(self, id: PyObjectId, _info):
        return str(id)

    @classmethod
    def str_name(cls, *args, **kwargs):
        return cls.model_json_schema(*args, **kwargs).get("title", "").lower()

    def renew_id(self):
        self.id = PyObjectId()

    def get_dict(self, exclude=[]):
        basic = ["status", "message", "res_data"]
        d = self.model_copy(deep=True).model_dump(
            exclude=set().union(basic, exclude)
        )
        return d

    def get_dict_copy(self, exclude=[]):
        return self.get_dict(exclude=exclude)

    def rec_name_domain(self):
        return {"rec_name": self.rec_name}.copy()

    def id_domain(self):
        return {"_id": bson.ObjectId(self.id)}.copy()

    def get_dict_diff(
        self,
        to_compare_dict: dict,
        ignore_fields: list = None,
        remove_ignore_fileds: bool = True,
    ):
        if ignore_fields is None:
            ignore_fields = []
        if ignore_fields and remove_ignore_fileds:
            original_dict = self.get_dict(exclude=ignore_fields)
        else:
            original_dict = self.get_dict()
        diff = {
            k: v
            for k, v in to_compare_dict.items()
            if k in original_dict and not original_dict[k] == v
        }
        return diff.copy()

    def is_error(self):
        return self.status == "error"

    def is_to_delete(self):
        return self.deleted > 0

    def set_active(self):
        self.deleted = 0
        self.active = True

    def set_archive(self):
        self.deleted = 0
        self.active = False

    def set_to_delete(self, timestamp):
        self.deleted = timestamp
        self.active = False

    def set_list_order(self, val):
        self.list_order = val

    @classmethod
    def get_value_for_select_list(cls, list_src, key, label_key="label"):
        for item in list_src:
            if item.get("value") == key:
                return item.get(label_key)
        return ""

    def selection_value_resources(
        self, key: str, value: str, resources: list, label_key: str = "label"
    ):
        value_label = self.get_value_for_select_list(
            resources, value, label_key=label_key
        )
        self.selection_value(key, value, value_label)

    @classmethod
    def no_clone_field_keys(cls):
        return ["list_order"]

    def clone_data(self):
        dat = self.get_dict_copy(exclude=self.no_clone_field_keys())
        return dat.copy()

    def to_datetime(self, key):
        v = self.get(key)
        try:
            return parse(v)
        except Exception:
            return v

    @classmethod
    def tranform_data_value(cls):
        return {}

    @classmethod
    def fields_limit_value(cls):
        return {}

    @classmethod
    def create_task_action(cls):
        return []

    @classmethod
    def fields_properties(cls):
        return {}

    @classmethod
    def default_hidden_fields(cls):
        return []

    @classmethod
    def default_readonly_fields(cls):
        return []

    @classmethod
    def default_disabled_fields(cls):
        return []

    @classmethod
    def default_required_fields(cls):
        return []

    @classmethod
    def realted_fields_logic(cls):
        return {}

    @classmethod
    def fields_logic(cls):
        return {}

    @classmethod
    def fields_conditional(cls):
        return {}

    @classmethod
    def filter_keys(cls):
        return []

    @classmethod
    def components_ext_data_src(cls):
        return []

    @classmethod
    def get_data_model(cls):
        return ""

    @classmethod
    def get_version(cls):
        return ""


class BasicModel(CoreModel):
    rec_name: str = ""

    @classmethod
    def get_unique_fields(cls) -> []:
        return ["rec_name"]

    @classmethod
    def computed_fields(cls) -> {}:
        return {}

    @classmethod
    def no_clone_field_keys(cls) -> []:
        return ["rec_name", "list_order"]

    @classmethod
    def config_fields(cls) -> {}:
        return {}

    @classmethod
    def conditional(cls) -> {str, dict}:
        return {}

    @classmethod
    def logic(cls) -> {str, list}:
        return {}


class AttachmentTrash(BasicModel):
    parent: str = ""
    model: str = ""
    # modell_ because model_rec_name has conflict with protected namespace "model_".
    modell_rec_name: str = ""
    attachments: List[Dict] = []


class Component(BasicModel):
    title: str = ""
    path: str = ""
    parent: str = ""
    parent_name: str = ""
    components: List[dict] = []
    links: Dict = {}
    type: str = "form"
    no_cancel: int = 0
    display: str = ""
    action: str = ""
    tags: Optional[List[str]] = []
    settings: Dict = {}
    properties: Dict = {}
    handle_global_change: int = 1
    process_tenant: str = ""
    make_virtual_model: bool = False
    authenticate: bool = True
    projectId: str = ""  # needed for compatibility with fomriojs

    @classmethod
    def get_unique_fields(cls):
        return ["rec_name", "title"]


class Session(CoreModel):
    parent_session: str = ""
    app_code: str = ""
    uid: str
    token: str = ""
    req_id: str = ""
    childs: list[Dict] = []
    login_complete: bool = False
    last_update: float = 0
    is_admin: bool = False
    use_auth: bool = False
    is_api: bool = False
    is_public: bool = False
    full_name: str = ""
    divisione_uo: str = ""
    user_function: str = ""
    function: str = ""
    sector: Optional[str] = ""
    sector_id: Optional[int] = 0
    expire_datetime: datetime
    user: dict = {}
    app: dict = {}
    apps: dict = {}
    queries: dict = {}
    action: dict = {}
    server_settings: dict = {}
    record: dict = {}

    @classmethod
    def get_unique_fields(cls):
        return ["token"]

    @classmethod
    def no_clone_field_keys(cls):
        return ["token", "list_order"]


class DictRecord(BaseModel):
    model: str
    rec_name: str = ""
    data: dict = {}

    def __init__(self, **data):
        super().__init__(**data)
        if not self.data.get("data_value"):
            self.data["data_value"] = {}
        else:
            self.data["rec_name"] = self.rec_name

    @property
    def data_value(self):
        return self.data.get("data_value", {})

    def parse_value(self, v):
        type_def = {
            "int": int,
            "string": str,
            "float": float,
            "dict": dict,
            "list": list,
            "datetime": datetime,
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
            return parse(dtr.group(0))
        else:
            rgx = regex.search(s)
            if not rgx:
                return s
            if s in ["false", "true"]:
                return bool("true" == s)
            if rgx.lastgroup not in ["list", "dict"]:
                types_d = []
                for match in regex.finditer(s):
                    types_d.append(match.lastgroup)
                if len(types_d) > 1:
                    return s
                else:
                    return type_def.get(rgx.lastgroup)(s)
            else:
                return json.load(s)

    def value_type(self, v):
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

    def selection_value(self, key, value, read_value):
        self.data[key] = value
        self.data["data_value"][key] = read_value

    def selection_value_from_record(self, key, src, src_key=""):
        if not src_key:
            src_key = key
        self.data[key] = src.data[src_key]
        self.data["data_value"][key] = src.data["data_value"][src_key]

    def get_dict(self):
        return json.loads(self.model_dump_json())

    def rec_name_domain(self):
        return {"rec_name": self.rec_name}.copy()

    def set_active(self, user_name="admin"):
        self.data["deleted"] = 0
        self.data["active"] = True
        self.data["owner_uid"] = user_name
        self.data["list_order"] = 0
        if "data_value" not in self.data:
            self.data["data_value"] = {}

    def set_list_order(self, val):
        self.data["list_order"] = val

    def scan_data(self, key, default=None):
        try:
            _keys = key.split(".")
            keys = []
            for v in _keys:
                if str(v).isdigit():
                    keys.append(int(v))
                else:
                    keys.append(v)
            lastplace = reduce(operator.getitem, keys[:-1], self.data)
            return lastplace.get(keys[-1], default)
        except Exception:
            return default

    def get(self, val, default: Optional = None):
        if "." in val:
            return self.scan_data(val, default)
        if default:
            return self.data.get(val, default)
        else:
            return self.data.get(val)

    def set(self, key, val, pase_data=True):
        if pase_data:
            self.data[key] = self.parse_value(val)
        else:
            self.data[key] = val

    def set_from_child(self, key, nodes: str, default):
        self.data[key] = self.get(nodes, default)

    def update_field_type_value(self, key):
        val = self.data.get(key, "")
        self.data[key] = self.parse_value(val)

    def set_many(self, data_dict):
        self.data.update(data_dict)

    def get_value_for_select_list(self, list_src, key, label_key="label"):
        for item in list_src:
            if item.get("value") == key:
                return item.get(label_key)
        return ""

    def selection_value_resources(
        self, key, value, list_src, label_key="label"
    ):
        value_label = self.get_value_for_select_list(
            list_src, value, label_key=label_key
        )
        self.selection_value(key, value, value_label)

    def to_date(self, key):
        v = self.get(key)
        if self.value_type(v) is datetime:
            return parse(v)
        return v

    def clone_data(self):
        dat = copy.deepcopy(self.data)
        dat.pop("rec_name")
        dat.pop("list_order")
        return dat.copy()


class BasicReturn(BaseModel):
    fail: bool = False
    msg: str = ""
    data: dict = {}


class Settings(BasicModel):
    list_order: Optional[int] = Field(0, title='List Order')
    rec_name: Optional[str] = Field('', title='Rec Name')
    internal_port: Optional[int] = Field(0, title='Internal Port')
    app_origin_type: Optional[str] = Field('', title='App Origin Type')
    module_label: Optional[str] = Field('', title='Module Label')
    description: Optional[str] = Field('', title='Description')
    admins: Optional[List[str]] = Field([], title='Admins')
    module_type: Optional[str] = Field('app', title='Module Type')
    module_group: Optional[str] = Field('', title='Module Group')
    version: Optional[str] = Field('1.0.0', title='Version')
    port: Optional[int] = Field(0, title='Port')
    stato: Optional[str] = Field('', title='Stato')
    upload_folder: Optional[str] = Field('/uploads', title='Upload Folder')
    web_concurrency: Optional[int] = Field(1, title='Web Concurrency')
    delete_record_after_days: Optional[int] = Field(
        1, title='Delete Record After Days'
    )
    session_expire_hours: Optional[int] = Field(
        12, title='Session Expire Hours'
    )
    theme: Optional[str] = Field('italia', title='Theme')
    logo_img_url: Optional[str] = Field('', title='Logo Img Url')
    server_datetime_mask: Optional[str] = Field(
        '%Y-%m-%dT%H:%M:%S', title='Server Datetime Mask'
    )
    server_date_mask: Optional[str] = Field(
        '%Y-%m-%dT%H:%M:%S', title='Server Date Mask'
    )
    ui_datetime_mask: Optional[str] = Field(
        '%d/%m/%Y %H:%M:%S', title='Ui Datetime Mask'
    )
    ui_date_mask: Optional[str] = Field('%d/%m/%Y', title='Ui Date Mask')
    tz: Optional[str] = Field('Europe/Rome', title='Tz')
    report_orientation: Optional[str] = Field(
        'Portrait', title='Report Orientation'
    )
    report_page_size: Optional[str] = Field('A4', title='Report Page Size')
    report_footer_company: Optional[str] = Field(
        '', title='Report Footer Company'
    )
    report_footer_title1: Optional[str] = Field(
        '', title='Report Footer Title1'
    )
    report_footer_sub_title: Optional[str] = Field(
        '', title='Report Footer Sub Title'
    )
    report_footer_pagination: Optional[bool] = Field(
        True, title='Report Footer Pagination'
    )
    report_header_space: Optional[str] = Field(
        '30mm', title='Report Header Space'
    )
    report_footer_space: Optional[str] = Field(
        '8mm', title='Report Footer Space'
    )
    report_margin_left: Optional[str] = Field(
        '10mm', title='Report Margin Left'
    )
    report_margin_right: Optional[str] = Field(
        '10mm', title='Report Margin Right'
    )

    @classmethod
    def get_version(cls):
        return '2022-08-01T10:11:04.635610'

    @classmethod
    def get_unique_fields(cls):
        return ['rec_name']

    @classmethod
    def computed_fields(cls):
        return {}

    @classmethod
    def no_clone_field_keys(cls):
        return ['rec_name']

    @classmethod
    def tranform_data_value(cls):
        return {}

    @classmethod
    def fields_limit_value(cls):
        return {}

    @classmethod
    def create_task_action(cls):
        return []

    @classmethod
    def fields_properties(cls):
        return {'admins': {'label': 'full_name', 'id': 'uid'}}

    @classmethod
    def default_hidden_fields(cls):
        return []

    @classmethod
    def default_readonly_fields(cls):
        return []

    @classmethod
    def default_required_fields(cls):
        return [
            'rec_name',
            'internal_port',
            'app_origin_type',
            'module_label',
            'description',
            'module_type',
            'module_group',
            'version',
            'port',
            'theme',
            'server_datetime_mask',
            'server_date_mask',
            'ui_datetime_mask',
            'tz',
            'report_orientation',
            'report_page_size',
            'report_header_space',
            'report_footer_space',
            'report_margin_left',
            'report_margin_right',
        ]

    @classmethod
    def filter_keys(cls):
        return [
            'list_order',
            'rec_name',
            'internal_port',
            'app_origin_type',
            'module_label',
            'description',
            'admins',
            'module_type',
            'module_group',
            'version',
            'port',
            'stato',
            'upload_folder',
            'web_concurrency',
            'delete_record_after_days',
            'session_expire_hours',
            'theme',
            'logo_img_url',
            'server_datetime_mask',
            'server_date_mask',
            'ui_datetime_mask',
            'ui_date_mask',
            'tz',
            'report_orientation',
            'report_page_size',
            'report_footer_company',
            'report_footer_title1',
            'report_footer_sub_title',
            'report_footer_pagination',
            'report_header_space',
            'report_footer_space',
            'report_margin_left',
            'report_margin_right',
            'domain',
            'external_proxy_uri_configs',
        ]

    @classmethod
    def config_fields(cls):
        return {
            'list_order': {
                'ctype': 'number',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': False,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'rec_name': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'internal_port': {
                'ctype': 'number',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'app_origin_type': {
                'ctype': 'select',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'selectComponent',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
                'valueProperty': None,
                'selectValues': None,
                'defaultValue': '',
                'multiple': False,
                'dataSrc': 'values',
                'idPath': '',
                'resource_id': '',
                'values': [
                    {'label': 'System', 'value': 'system'},
                    {'label': 'Virtual', 'value': 'virtual'},
                ],
                'template_label_keys': [],
            },
            'module_label': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'description': {
                'ctype': 'textarea',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'admins': {
                'ctype': 'select',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': False,
                'unique': False,
                'component': 'selectComponent',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
                'valueProperty': None,
                'selectValues': None,
                'defaultValue': '',
                'multiple': True,
                'dataSrc': 'url',
                'idPath': '',
                'resource_id': '',
                'values': [],
                'url': 'https://people.ininrim.it/api'
                '/get_addressbook_service_user/0',
                'template_label_keys': [],
            },
            'module_type': {
                'ctype': 'select',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'selectComponent',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
                'valueProperty': None,
                'selectValues': None,
                'defaultValue': 'app',
                'multiple': False,
                'dataSrc': 'values',
                'idPath': '',
                'resource_id': '',
                'values': [
                    {'label': 'App', 'value': 'app'},
                    {'label': 'Backend', 'value': 'server'},
                ],
                'template_label_keys': [],
            },
            'module_group': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'version': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'port': {
                'ctype': 'number',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'stato': {
                'ctype': 'select',
                'disabled': True,
                'readonly': False,
                'hidden': False,
                'required': False,
                'unique': False,
                'component': 'selectComponent',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
                'valueProperty': None,
                'selectValues': None,
                'defaultValue': '',
                'multiple': False,
                'dataSrc': 'values',
                'idPath': '',
                'resource_id': '',
                'values': [
                    {'label': 'Attivo', 'value': 'live'},
                    {'label': 'Spento', 'value': 'spento'},
                ],
                'template_label_keys': [],
            },
            'upload_folder': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': False,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'web_concurrency': {
                'ctype': 'number',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': False,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'delete_record_after_days': {
                'ctype': 'number',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': False,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'session_expire_hours': {
                'ctype': 'number',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': False,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'theme': {
                'ctype': 'select',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'selectComponent',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
                'valueProperty': None,
                'selectValues': None,
                'defaultValue': 'italia',
                'multiple': False,
                'dataSrc': 'values',
                'idPath': '',
                'resource_id': '',
                'values': [{'label': 'Italia', 'value': 'italia'}],
                'template_label_keys': [],
            },
            'logo_img_url': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': False,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'server_datetime_mask': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'server_date_mask': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'ui_datetime_mask': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'ui_date_mask': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': False,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'tz': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'report_orientation': {
                'ctype': 'select',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'selectComponent',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
                'valueProperty': None,
                'selectValues': None,
                'defaultValue': 'Portrait',
                'multiple': False,
                'dataSrc': 'values',
                'idPath': '',
                'resource_id': '',
                'values': [
                    {'label': 'Portrait', 'value': 'Portrait'},
                    {'label': 'Landscape', 'value': 'Landscape'},
                ],
                'template_label_keys': [],
            },
            'report_page_size': {
                'ctype': 'select',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'selectComponent',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
                'valueProperty': None,
                'selectValues': None,
                'defaultValue': 'A4',
                'multiple': False,
                'dataSrc': 'values',
                'idPath': '',
                'resource_id': '',
                'values': [
                    {'label': 'Legal', 'value': 'Legal'},
                    {'label': 'Letter', 'value': 'Letter'},
                    {'label': 'A4', 'value': 'A4'},
                    {'label': 'A3', 'value': 'A3'},
                ],
                'template_label_keys': [],
            },
            'report_footer_company': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': False,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'report_footer_title1': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': False,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'report_footer_sub_title': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': False,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'report_footer_pagination': {
                'ctype': 'checkbox',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': False,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'report_header_space': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'report_footer_space': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'report_margin_left': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'report_margin_right': {
                'ctype': 'textfield',
                'disabled': False,
                'readonly': False,
                'hidden': False,
                'required': True,
                'unique': False,
                'component': 'Component',
                'calculateServer': None,
                'action_type': False,
                'no_clone': False,
                'transform': {},
                'datetime': False,
                'min': False,
                'max': False,
            },
            'external_proxy_uri_configs': {},
        }

    @classmethod
    def components_ext_data_src(cls):
        return ['admins']

    @classmethod
    def get_data_model(cls):
        return ""
