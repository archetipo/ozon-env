# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from typing import TypeVar
from db.BsonTypes import (
    Decimal128,
    DateTime,
    BSON_TYPES_ENCODERS,
    PyObjectId,
    bson,
)
import ujson
import logging
import copy

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
    "owner_uid",
    "owner_name",
    "owner_sector",
    "owner_sector_id",
    "owner_function",
    "create_datetime",
    "owner_mail",
    "owner_personal_type",
    "owner_job_title",
    "list_order",
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


class CoreModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    app_code: Optional[List] = []
    parent: str = ""
    process_id: str = ""
    process_task_id: str = ""
    data_value: Dict = {}
    owner_name: str = ""
    deleted: Decimal128 = 0
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
    childs: List[Any] = []
    create_datetime: DateTime = Field(default="1970-01-01T00:00:00")
    update_datetime: DateTime = Field(default="1970-01-01T00:00:00")

    @classmethod
    def str_name(cls, *args, **kwargs):
        return cls.schema(*args, **kwargs).get("title", "").lower()

    def renew_id(self):
        self.id = PyObjectId()

    def get_dict(self):
        return ujson.loads(self.json())

    def get_dict_copy(self):
        return copy.deepcopy(self.get_dict())

    def rec_name_domain(self):
        return {"rec_name": self.rec_name}.copy()

    def id_domain(self):
        return {"_id": bson.ObjectId(self.id)}.copy()

    def get_dict_diff(
        self, to_compare_dict, ignore_fields=[], remove_ignore_fileds=True
    ):
        original_dict = self.dict().copy()
        if ignore_fields and remove_ignore_fileds:
            [
                original_dict.pop(key)
                for key in ignore_fields
                if key in original_dict
            ]
        diff = {
            k: v
            for k, v in to_compare_dict.items()
            if k in original_dict and not original_dict[k] == v
        }
        return diff.copy()

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = BSON_TYPES_ENCODERS


class BasicModel(CoreModel):
    rec_name: str = ""


class AttachmentTrash(BasicModel):
    rec_name: str = ""
    parent: str = ""
    model: str = ""
    model_rec_name: str = ""
    attachments: List[Dict] = []

    @classmethod
    def get_unique_fields(cls):
        return ["rec_name"]


class Component(BasicModel):
    title: str = ""
    data_model: str = ""
    path: str = ""
    parent: str = ""
    parent_name: str = ""
    components: List[Dict] = []
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
    childs: List[Any] = []
    login_complete: bool = False
    last_update: Decimal128 = 0
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


def update_model(
    source, object_o: BasicModel, pop_form_newobject=[], model=None
):
    new_dict = object_o.get_dict()
    new_dict["id"] = source.dict()["id"]
    if model is not None:
        object_o = model(**new_dict)
    else:
        object_o = type(source)(**new_dict)
    return object_o
