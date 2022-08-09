import json
from datetime import datetime
from BaseModels import BaseModel
from typing import Optional
import re
import copy
import logging
import operator
from functools import reduce
from dateutil.parser import parse

logger = logging.getLogger("asyncio")

TYPE_VALUE_DEFAULT = {
    int: 0,
    float: 0.0,
    list: [],
    dict: {},
    str: "",
    datetime: "1970-01-01T00:00:00",
}


class Record(BaseModel):
    model: str
    rec_name: str = ""
    data: dict = {}
    status: str = "ok"
    message: str = ""

    def __init__(self, **data):
        super().__init__(**data)
        if not self.rec_name:
            self.data["data_value"] = {}
        else:
            self.data["rec_name"] = self.rec_name

    @property
    def is_error(self):
        return self.status == "error"

    @property
    def is_active(self):
        return self.data["active"] is True

    @property
    def is_to_delete(self):
        return self.data.get("deleted") > 0

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

    def selction_value(self, key, value, read_value):
        self.data[key] = value
        self.data["data_value"][key] = read_value

    def selction_value_from_record(self, key, src, src_key=""):
        if not src_key:
            src_key = key
        self.data[key] = src.data[src_key]
        self.data["data_value"][key] = src.data["data_value"][src_key]

    def get_dict(self):
        return json.loads(self.json())

    def rec_name_domain(self):
        return {"rec_name": self.rec_name}.copy()

    def set_active(self):
        self.data["deleted"] = 0
        self.data["active"] = True

    def set_archive(self):
        self.data["deleted"] = 0
        self.data["active"] = False

    def set_to_delete(self, timestamp):
        self.data["deleted"] = timestamp
        self.data["active"] = False

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
        except Exception as e:
            print(f" error scan_data {e}")
            return default

    def get(self, val, default: Optional = None):
        if "." in val:
            return self.scan_data(val, default)
        elif default:
            return self.data.get(val, default)
        else:
            return self.data.get(val)

    def set(self, key, val, pase_data=True):
        if pase_data:
            self.data[key] = self.parse_value(val)
        else:
            self.data[key] = val
        if key == "rec_name":
            self.rec_name = self.data[key]

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
        self.selction_value(key, value, value_label)

    def to_datetime(self, key):
        v = self.get(key)
        if self.value_type(v) is datetime:
            return parse(v)
        return v

    def clone_data(self):
        dat = copy.deepcopy(self.data)
        dat.pop("rec_name")
        dat.pop("list_order")
        return dat.copy()
