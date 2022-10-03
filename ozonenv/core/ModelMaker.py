# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from typing import List
from pydantic import create_model
from pydantic.main import ModelMetaclass
from datetime import datetime, date
from ozonenv.core.BaseModels import BasicModel, BaseModel, MainModel
from ozonenv.core.utils import (
    fetch_dict_get_value,
    is_json,
    decode_resource_template,
)
import logging
import re
import uuid
import copy
import json
from json_logic import jsonLogic

logger = logging.getLogger(__file__)


class Component:
    def __init__(self, raw, builder, **kwargs):
        # TODO or provide the Builder object?
        # raw =
        # super().__init__(copy.deepcopy(raw), builder, **kwargs)

        # TODO i18n (language, translations)
        self.raw = copy.deepcopy(raw)
        self.builder = builder
        self.tmpe = None
        self.theme_cfg = None
        self.is_mobile = False
        self.modal = False
        self.default_data = {self.key: ""}
        self.survey = False
        self.multi_row = False
        self.tabs = False
        self.dataSrc = False
        self.table = False
        self.search_area = False
        self.uploaders = False
        self.scanner = False
        self.stepper = False
        self.is_html = False
        self._parent = ""
        self.grid_rows = []
        self.form_data = {}
        self.raw_key = ""
        self.key_prefix = ""
        self.parent_key = ""
        self.component_tmp = self.raw.get("type")
        self.req_id = ""
        self.language = kwargs.get("language", "it")
        self.i18n = kwargs.get("i18n", {})
        self.clean = re.compile("<.*?>")
        self.resources = kwargs.get("resources", [])
        self.defaultValue = self.raw.get("defaultValue")
        self._value = None
        self.input_type = kwargs.get("input_type", str)
        self.nested = kwargs.get("nested", [])
        self.cfg = {}
        self.index = 0
        self.iindex = 0
        self.update_config()

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, id=False):
        if not id:
            id = str(uuid.uuid4())
        self._id = id

    @property
    def value(self):
        if self._parent:
            obj = getattr(self.builder.instance, self._parent)
            return getattr(obj[self.iindex], self.key)
        return getattr(self.builder.instance, self.key)

    @property
    def key(self):
        return self.raw.get("key")

    @key.setter
    def key(self, value):
        self.raw["key"] = value

    @property
    def input(self):
        return bool(self.raw.get("input"))

    @property
    def label(self):
        label = self.raw.get("label")
        if self.i18n.get(self.language):
            return self.i18n[self.language].get(label, label) or ""
        else:
            return label or ""

    @label.setter
    def label(self, value):
        if self.raw.get("label"):
            self.raw["label"] = value

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        if parent:
            self._parent = parent

    @property
    def type(self):
        return self.raw.get("type")

    @property
    def tableView(self):
        return self.raw.get("tableView", False)

    @property
    def hideLabel(self):
        return self.raw.get("hideLabel", False)

    @property
    def hidden(self):
        return self.cfg.get("hidden")

    @property
    def disabled(self):
        return self.cfg.get("disabled")

    @property
    def readonly(self):
        return self.cfg.get("readonly")

    @property
    def unique(self):
        return self.cfg.get("unique")

    @property
    def required(self):
        return self.cfg.get("required")

    @property
    def calculateServer(self):
        return self.cfg.get("calculateServer", False)

    @property
    def action_type(self):
        return self.cfg.get("action_type")

    @property
    def no_clone(self):
        if self.calculateServer:
            return True
        return self.cfg.get("no_clone")

    @property
    def trigger_change(self):
        trig_chage = False
        if self.raw.get("properties") and self.raw.get("properties").get(
            "trigger_change"
        ):
            trig_chage = True
        return trig_chage

    @property
    def has_logic(self):
        return self.raw.get("logic", False)

    @property
    def has_conditions(self):
        return isinstance(self.raw.get("conditional", {}).get("json"), dict)

    @property
    def properties(self):
        p = self.raw.get("properties", {})
        if not isinstance(p, dict):
            self.raw["properties"] = {}
        return self.raw.get("properties", {})

    @property
    def validate(self):
        return self.raw.get("validate", {})

    @property
    def transform(self):
        return self.cfg.get("transform", False)

    @property
    def limit_values(self):
        if self.cfg.get("min") or self.cfg.get("max"):
            return {"min": self.cfg.get("min"), "max": self.cfg.get("max")}
        return False

    @property
    def childs(self):
        return self.nested

    @childs.setter
    def childs(self, val):
        self.nested.append(val)
        self.index = len(self.nested)
        self.iindex = 0

    @property
    def child(self):
        o = self.nested[0]
        for item in o:
            o[item].iindex = self.iindex
        return o

    def childs_reset(self):
        self.iindex = 0

    def next(self):
        obj = getattr(self.builder.instance, self.key)
        maxx = len(obj)
        self.iindex += 1
        if self.iindex > maxx - 1:
            self.iindex = maxx - 1

    def update_config(self):
        if not self.raw.get("properties"):
            self.raw["properties"] = {}
        if not self.raw.get("validate"):
            self.raw["validate"] = {}
        self.cfg["disabled"] = self.raw.get("disabled", False)
        ro = self.raw.get("readOnlyValue", False)
        if self.properties.get("readonly"):
            ro = True
        self.cfg["readonly"] = ro
        self.cfg["hidden"] = self.raw.get("hidden", False)
        req = self.validate.get("required", False)
        if self.properties.get("required"):
            req = True
        self.cfg["required"] = req
        self.cfg["unique"] = self.validate.get("unique", False)
        calc_server = self.raw.get("calculateValue") and self.raw.get(
            "calculateValue", False
        )
        if not calc_server and self.properties.get("calculateServer", False):
            calc_server = self.properties.get("calculateServer")
        self.cfg["calculateServer"] = calc_server
        self.cfg["action_type"] = self.properties.get("action_type", False)
        self.cfg["no_clone"] = self.properties.get("no_clone", False)
        self.cfg["transform"] = {}
        self.cfg["datetime"] = False
        self.cfg["min"] = False
        self.cfg["max"] = False
        if self.type == "datetime":
            self.cfg["date"] = self.raw.get("enableDate", True)
            self.cfg["time"] = self.raw.get("enableTime", True)
            if self.cfg["date"] is True:
                self.cfg["transform"] = {"type": date}
            if self.cfg["date"] is True and self.cfg["time"] is True:
                self.cfg["datetime"] = True
                self.cfg["transform"] = {"type": datetime}
            self.cfg["min"] = self.raw["widget"]["minDate"]
            self.cfg["max"] = self.raw["widget"]["maxDate"]
        if self.raw.get("requireDecimal") is True:
            self.cfg["mask"] = self.raw.get("displayMask", "decimal")
            self.cfg["min"] = self.validate.get("min")
            self.cfg["max"] = self.validate.get("max")
            self.cfg["delimiter"] = self.raw.get("delimiter", ",")
            self.cfg["dp"] = self.raw.get("decimalLimit", 2)
            self.cfg["transform"] = {
                "type": float,
                "dp": self.cfg["dp"],
                "mask": self.cfg["mask"],
                "dps": self.cfg["delimiter"],
            }

    def aval_conditional(self):
        if self.raw.get("conditional").get("json"):
            json_logic = self.raw.get("conditional").get("json")
            self._find_logic_rel_fields(json_logic)
            res = not jsonLogic(json_logic, self.builder.context_data)
            self.cfg["hidden"] = res

    def eval_action_value_json_logic(self, act_value):
        data = is_json(act_value)
        if not data:
            return act_value
        self._find_logic_rel_fields(data)
        logic_data = jsonLogic(data, self.builder.context_data)
        return logic_data

    def apply_action(self, action, logic_res):
        # logger.debug(f"comupte apply_action--> {action}")
        if action.get("type") == "property":
            item = action.get("property").get("value")
            value = action.get("state")
            if "validate" in item:
                item = item.split(".")[1]
            self.cfg[item] = value
            # logger.debug(f"{item} --> {self.cfg[item]}")
        elif action.get("type") == "value":
            if "=" not in action.get("value"):
                key = action.get("value")
                res = logic_res
            else:
                func = action.get("value").strip().split("=", 1)
                key = func[0].strip()
                elem = func[1]
                res = self.eval_action_value_json_logic(elem)
            if key == "value":
                self.cfg[key] = self.input_type(res)
            else:
                self.cfg[key] = res
            # logger.info(f"complete <--> {self.cfg[key]} = {res}")
            # logger.info(f"complete <--> {self.cfg[key]}")
            if not key == "value":
                self.properties[key] = self.cfg[key]

    def compute_logic(self, json_logic, actions):
        logic_res = jsonLogic(json_logic, self.builder.context_data)
        # logger.info(f"comupte json_logic--> {json_logic}  -> {logic_res}")
        if logic_res:
            for action in actions:
                if action:
                    self.apply_action(action.copy(), logic_res)

    def eval_logic(self):
        # logger.info(f"before_logic {self.raw['key']}")
        if self.raw.get("logic"):
            for logic in self.raw.get("logic"):
                if logic.get("trigger") and logic.get("trigger").get("json"):
                    actions = logic.get("actions", [])
                    json_logic = logic.get("trigger").get("json")
                    self._find_logic_rel_fields(json_logic)
                    self.compute_logic(json_logic, actions)
        return self.cfg.copy()

    def _find_logic_rel_fields(self, json_logic):
        for k, v in json_logic.copy().items():
            if isinstance(v, dict):  # For DICT
                self._find_logic_rel_fields(v)
            elif isinstance(v, list):  # For LIST
                [
                    self._find_logic_rel_fields(i)
                    for i in v
                    if isinstance(i, dict)
                ]
            else:  # Update Key-Value
                if k == "var" and "form." in v:
                    vals = v.split(".")
                    val = ""
                    if "form.data_value" in v:
                        val = vals[2]
                    else:
                        val = vals[1]
                    if val:
                        if val not in self.builder.realted_fields_logic:
                            self.builder.realted_fields_logic[val] = []
                        if (
                            self.key
                            not in self.builder.realted_fields_logic[val]
                        ):
                            self.builder.realted_fields_logic[val].append(
                                self.key
                            )

    def compute_logic_and_condition(self):
        if self.has_logic:
            self.eval_logic()
        if self.has_conditions:
            self.aval_conditional()

    def compute_data_table(self, data):
        return data.copy()

    def get_filter_object(self):
        return self.search_object.copy()

    def eval_components(self):
        if self.input:
            self.builder.components_keys.append(self.key)
        if self.search_area:
            self.builder.search_areas.append(self)
        if self.tableView:
            if not self.survey and not self.multi_row:
                self.builder.table_colums[self.key] = self.label
        if (
            self.key
            and self.key is not None
            and self.type not in ["columns", "column", "well", "panel"]
            and self.key not in self.builder.filter_keys
        ):
            self.builder.filters.append(self)
            self.builder.filter_keys.append(self.key)
        if self.has_logic or self.has_conditions:
            self.builder.components_logic.append(self)
        if not self.type == "table":
            self.compute_logic_and_condition()

    def compute_data(self):
        for component in self.component_items:
            component.compute_data()

    def load_data(self):
        for component in self.component_items:
            component.load_data()


class selectComponent(Component):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.ext_resource = False
        self.item_data = {}
        self.context_data = {}
        self.template_label_keys = []
        self.selected_id = ""
        self.resource_id = ""
        self.url = ""
        self.header_key = ""
        self.header_value_key = ""
        self.path_value = ""
        self.valueProperty = self.raw.get("valueProperty")
        self.selectValues = self.raw.get("selectValues")
        self.defaultValue = self.raw.get("defaultValue", "")
        self.idPath = self.raw.get("idPath", "")
        self.multiple = self.raw.get("multiple", False)
        if self.dataSrc and self.dataSrc == "resource":
            if self.raw.get("template"):
                self.template_label_keys = decode_resource_template(
                    self.raw.get("template")
                )
            else:
                self.template_label_keys = decode_resource_template(
                    "<span>{{ item.label }}</span>"
                )
            if self.raw.get("data") and self.raw.get("data").get("resource"):
                self.resource_id = self.raw.get("data") and self.raw.get(
                    "data"
                ).get("resource")
            if self.dataSrc and self.dataSrc == "url":
                self.url = self.raw.get("data").get("url")
                self.header_key = (
                    self.raw.get("data", {}).get("headers", {})[0].get("key")
                )
                self.header_value_key = (
                    self.raw.get("data", {}).get("headers", [])[0].get("value")
                )

    def make_resource_list(self):
        resource_list = self.resources
        self.raw["data"] = {"values": []}
        for item in resource_list:
            if self.dataSrc == "resource":
                label = fetch_dict_get_value(item, self.template_label_keys[:])
                iid = item["rec_name"]
            else:
                label = item[self.properties["label"]]
                iid = item[self.properties["id"]]
            self.search_object["values"].update({iid: label})
            self.raw["data"]["values"].append({"label": label, "value": iid})

    @property
    def value_label(self):
        comp = self.builder.components.get(self.key)
        values = comp.raw.get("data") and comp.raw["data"].get("values")
        for val in values:
            if comp.value and val["value"] == (type(val["value"])(comp.value)):
                label = val["label"]
                if self.i18n.get(self.language):
                    return self.i18n[self.language].get(label, label) or ""
                else:
                    return label or ""

    @property
    def value_labels(self):
        comp = self.builder.components.get(self.key)
        values = comp.raw.get("data") and comp.raw["data"].get("values")
        value_labels = []
        for val in values:
            if val and self.value and str(val["value"]) in self.value:
                if self.i18n.get(self.language):
                    value_labels.append(
                        self.i18n[self.language].get(
                            val["label"], val["label"]
                        )
                    )
                else:
                    value_labels.append(val["label"])
        return value_labels or []

    @property
    def data(self):
        return self.raw.get("data")

    @property
    def values(self):
        return self.raw.get("data", {}).get("values")

    def get_default(self):
        """
        search default in context_data i.e. --> default  'user.uid'
        context data contain dict --> 'user' and user is a dict that
        contain property 'uid'
        If exist in context exist user.uid the value is set as default.
        """
        default = self.defaultValue
        if self.multiple:
            if self.defaultValue:
                default = [self.defaultValue]
            else:
                default = []

        if self.valueProperty and not self.selected_id:
            if "." in self.valueProperty:
                to_eval = self.valueProperty.split(".")
                if len(to_eval) > 0:
                    obj = self.builder.context_data.get(to_eval[0], {})
                    if obj and isinstance(obj, dict):
                        self.selected_id = obj.get(to_eval[1], "")
                if self.multiple:
                    default.append(self.selected_id)
                else:
                    default = self.selected_id
        return default


class surveyComponent(Component):
    @property
    def values_labels(self):
        comp = self.component_owner.input_components.get(self.key)
        builder_values = comp.raw.get("values")
        labels = []
        for val in builder_values:
            if self.i18n.get(self.language):
                label = self.i18n[self.language].get(
                    val["label"], val["label"]
                )
            else:
                label = val["label"]
            labels.append(label)
        return labels

    @property
    def questions(self):
        return self.raw.get("questions")

    @property
    def question_values(self):
        return self.raw.get("values")

    @property
    def grid(self):
        comp = self
        builder_questions = comp.raw.get("questions")
        builder_values = comp.raw.get("values")
        grid = []
        for question in builder_questions:
            # question
            if self.i18n.get(self.language):
                question_label = self.i18n[self.language].get(
                    question["label"], question["label"]
                )
            else:
                question_label = question["label"]
            question_dict = {
                "question_value": question["value"],
                "question_label": question_label,
                "values": [],
            }

            # value
            for b_val in builder_values:
                if self.i18n.get(self.language):
                    val_label = self.i18n[self.language].get(
                        b_val["label"], b_val["label"]
                    )
                else:
                    val_label = b_val["label"]

                value = {
                    "label": val_label,
                    "value": b_val["value"],
                    "checked": False
                    # default as fallback (if new values in builder)
                }

                if self.value.get(question["value"]):
                    value["checked"] = (
                        self.value[question["value"]] == b_val["value"]
                    )

                question_dict["values"].append(value)

            # append
            grid.append(question_dict)
        return grid


class BaseModelMaker:
    def __init__(self, model_name: str):
        self.components = {}
        self.components_keys = []
        self.model_form_fields = {}
        self.form_fields = {}
        self.form_fields_layout = {}
        self.context_data = {}
        self.simple = False
        self.model: ModelMetaclass
        self.instance: BasicModel = None
        self.components_todo = {}
        self.model_name = model_name
        self.unique_fields = ["rec_name"]
        self.required_fields = ["rec_name"]
        self.no_create_model_field_key = [
            "tabs",
            "columns",
            "button",
            "panel",
            "form",
            "fieldset",
            "resource",
            "table",
            "well",
            "htmlelement",
        ]
        self.layoyt_components = ["tabs", "columns", "panel"]
        self.no_clone_field_type = ["file"]
        self.no_clone_field_keys = {}
        self.computed_fields = {}
        self.create_task_action = {}
        self.create_model_to_nesteded = ["datagrid", "form", "table"]
        self.create_simple_model_to_nesteded = []
        self.linked_object = []
        self.select_recources = []
        self.mapper = {
            "textfield": [str, ""],
            "password": [str, ""],
            "file": [list[dict], []],
            "email": [str, ""],
            "content": [str, ""],
            "textarea": [str, ""],
            "number": [int, 0],
            "number_f": [float, 0.0],
            "select": [str, ""],
            "select_multi": [List[str], []],
            "checkbox": [bool, False],
            "radio": [str, ""],
            "survey": [dict, {}],
            "jsondata": [dict, {}],
            "datetime": [datetime, "1970-01-01T00:00:00"],
            "datagrid": [list[dict], []],
            "table": [list[dict], []],
            "form": [list[dict], {}],
        }
        self.fields_list = []
        self.parent = None
        self.parent_builder = None
        self.virtual = False
        self.filter_keys = []
        self.realted_fields_logic = {}
        self.search_areas = []
        self.table_colums = {}
        self.filters = []
        self.filter_keys = []
        self.components_logic = []
        self.tranform_data_value = {}
        self.fields_limit_value = {}
        self.schema_object = None

    def get_field_value(self, v):
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
            return dtr.group(0)
        else:
            rgx = regex.search(s)
            if not rgx:
                return s
            if s in ["false", "true", "True", "False"]:
                return bool("true" == s)
            if rgx.lastgroup not in ["list", "dict"]:
                types_d = []
                for match in regex.finditer(s):
                    types_d.append(match.lastgroup)
                if len(types_d) > 1:
                    return s
                else:
                    # fing group value in groupdict
                    # i present the real value matched
                    # take it to return the real value cleaned
                    # from nosisy charter
                    if rgx.lastgroup in ["int", "float"]:
                        return type_def.get(rgx.lastgroup)(
                            rgx.groupdict().get(rgx.lastgroup)
                        )
                    else:
                        return type_def.get(rgx.lastgroup)(s)
            else:
                if type(s) is str and rgx.lastgroup in ["list", "dict"]:
                    try:
                        return json.loads(s)
                    except Exception as e:
                        logger.error(f" in decode {s}")
                        logger.error(e, exc_info=True)
                        return s
                else:
                    return s

    def get_field_type(self, v):
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
            if s in ["false", "true", "True", "False"]:
                return bool
            types_d = []
            for match in regex.finditer(s):
                types_d.append(match.lastgroup)
            if len(types_d) > 1:
                return str
            else:
                return type_def.get(rgx.lastgroup)

    def parse_make_field(self, v, k=""):
        return (self.get_field_type(v), self.get_field_value(v))

    def _make_from_dict(self, dict_data, from_dict=False):
        for k, v in dict_data.copy().items():
            if isinstance(v, dict) and k != "data_value":  # For DICT
                dict_data[k] = self._make_from_dict(v)
            elif isinstance(v, dict) and k == "data_value":
                default = dict_data[k].copy()
                dict_data[k] = (dict, default.copy())
            elif isinstance(v, list):  # For LIST
                default = dict_data[k]
                dict_data[k] = []
                for i in v:
                    if isinstance(i, dict):
                        dict_data[k].append(self._make_from_dict(i))
                if not dict_data[k]:
                    dict_data[k] = (List[self.get_field_type(v)], default)
            else:  # Update Key-Value
                if k != "_id":
                    dict_data[k] = self.parse_make_field(v)
        return dict_data

    def _make_models(self, dict_data):
        for k, v in dict_data.copy().items():
            if isinstance(v, dict) and k != "data_value":  # For DICT
                val = self._make_models(v).copy()
                model = create_model(k, __base__=MainModel, **val)
                dict_data[k] = model(**{})
            elif isinstance(v, list):  # For LIST
                for idx, i in enumerate(v):
                    if isinstance(i, dict) and k != "data_value":
                        row = self._make_models(i).copy()
                        model = create_model(k, __base__=MainModel, **row)
                        dict_data[k][idx] = model(**{})
        return dict_data

    def from_data_dict(self, data):
        self.virtual = True
        components = self._make_from_dict(data)
        # TODO reactivate when pydantic is stable
        self.components = self._make_models(components)
        self.model = create_model(
            self.model_name, __base__=BasicModel, **self.components
        )

    def new(self, data={}):
        self.instance = self.model(**data)


class FormioModelMaker(BaseModelMaker):
    def __init__(self, model_name: str):
        super(FormioModelMaker, self).__init__(model_name=model_name)

    def from_formio(
        self, schema: dict, simple=False, parent="", parent_builder=None
    ):
        self.parent = parent
        self.parent_builder = parent_builder
        self.simple = simple
        self.components_todo = schema.get("components")[:]
        self.make()
        return self.model

    def add_nested(self, comp):
        field = Component(comp, self, input_type=None)
        nested = FormioModelMaker(comp.get("key"))
        nested_model = nested.from_formio(
            comp, parent=comp.get("key"), parent_builder=self
        )
        field.childs = nested.model_form_fields
        self.model_form_fields[field.key] = field
        self.components[comp.get("key")] = (List[nested_model], [])
        self.complete_component(field)

    def add_form(self, comp):
        self.add_nested(comp)

    def add_table(self, comp):
        self.add_nested(comp)

    def add_datagrid(self, comp):
        self.add_nested(comp)

    def complete_component(self, field: Component):
        if field.type == "table" and field:
            self.computed_fields[field.key] = field.calculateServer
        if field.type == "fieldset" and field.action_type:
            self.create_task_action[field.key] = field.properties.copy()
        try:
            field.eval_components()
        except Exception as e:
            logger.error(f"Error eval_components {field.key} {e}")

    def complete_component_field(self, comp, compo_todo):
        builder = self
        if self.parent_builder:
            builder = self.parent_builder
        self.components[comp.get("key")] = tuple(compo_todo)
        if comp.get("type") == "select":
            field = selectComponent(comp, builder, input_type=compo_todo[0])
        elif comp.get("type") == "survey":
            field = surveyComponent(comp, builder, input_type=compo_todo[0])
        elif comp.get("type") == "datetime":
            field = Component(comp, builder, input_type=str)
        else:
            field = Component(comp, builder, input_type=compo_todo[0])
        field.parent = self.parent
        if field.required:
            self.required_fields.append(field.key)
        if field.unique:
            self.unique_fields.append(field.key)
            self.no_clone_field_keys.update({field.key: compo_todo[1]})
        if field.calculateServer:
            self.computed_fields[field.key] = field.calculateServer
        if field.no_clone or field.key in self.unique_fields:
            self.no_clone_field_keys.update({field.key: compo_todo[1]})
        if field.transform:
            self.tranform_data_value[field.key] = field.transform.copy()
        if field.limit_values:
            self.fields_limit_value = field.limit_values.copy()
        self.complete_component(field)

    def add_textfield(self, comp):
        compo_todo = self.mapper.get("textfield")[:]
        self.complete_component_field(comp.copy(), compo_todo)

    def add_password(self, comp):
        compo_todo = self.mapper.get("password")[:]
        self.complete_component_field(comp.copy(), compo_todo)

    def add_numer_decimal(self, comp):
        compo_todo = self.mapper.get("number_f")[:]
        self.complete_component_field(comp.copy(), compo_todo)

    def add_number(self, comp):
        if comp.get("requireDecimal"):
            self.add_numer_decimal(comp)
        else:
            compo_todo = self.mapper.get("number")[:]
            self.complete_component_field(comp.copy(), compo_todo)

    def add_select(self, comp):
        if comp.get("multiple", False) is False:
            compo_todo = self.mapper.get("select")[:]
        else:
            compo_todo = self.mapper.get("select_multi")[:]

        self.complete_component_field(comp.copy(), compo_todo)

    def add_textarea_json(self, comp):
        compo_todo = self.mapper.get("jsondata")[:]
        self.complete_component_field(comp.copy(), compo_todo)

    def add_textarea(self, comp):
        if comp.get("properties", {}).get("type", "") == "json":
            self.add_textarea_json(comp)
        else:
            compo_todo = self.mapper.get("textarea")[:]
            self.complete_component_field(comp.copy(), compo_todo)

    def add_datetime(self, comp):
        compo_todo = self.mapper.get("datetime")[:]
        self.complete_component_field(comp.copy(), compo_todo)

    def add_day(self, comp):
        self.add_datetime(comp)

    def add_checkbox(self, comp):
        compo_todo = self.mapper.get("checkbox")[:]
        self.complete_component_field(comp.copy(), compo_todo)

    def add_radio(self, comp):
        compo_todo = self.mapper.get("radio")[:]
        self.complete_component_field(comp.copy(), compo_todo)

    def add_survey(self, comp):
        compo_todo = self.mapper.get("survey")[:]
        self.complete_component_field(comp.copy(), compo_todo)

    def add_content(self, comp):
        compo_todo = self.mapper.get("content")[:]
        self.complete_component_field(comp.copy(), compo_todo)

    def add_email(self, comp):
        compo_todo = self.mapper.get("email")[:]
        self.complete_component_field(comp.copy(), compo_todo)

    def add_file(self, comp):
        compo_todo = self.mapper.get("file")[:]
        self.complete_component_field(comp.copy(), compo_todo)

    def make_model(self):
        self.model = create_model(
            self.model_name, __base__=BasicModel, **self.components
        )
        logger.debug(f"Make model {self.model_name}... Done")

    def eval_columns(self, columns):
        for column in columns.get("columns"):
            for component in column["components"]:
                if component.get("type") not in self.no_create_model_field_key:
                    self.compute_component_field(component.copy())
                elif component.get("type") in self.layoyt_components:
                    self.eval_component(component.copy())

    def eval_panel(self, panel):
        for component in panel.get("components", []):
            if component.get("type") not in self.no_create_model_field_key:
                self.compute_component_field(component.copy())
            elif component.get("type") in self.layoyt_components:
                self.eval_component(component.copy())

    def eval_tabs(self, tabs):
        for tab in tabs.get("components", []):
            for component in tab["components"]:
                if component.get("type") not in self.no_create_model_field_key:
                    self.compute_component_field(component.copy())
                elif component.get("type") in self.layoyt_components:
                    self.eval_component(component.copy())

    def make_simple_model(self, fields_def):
        self.model = create_model(
            self.model_name, __base__=BaseModel, **fields_def
        )
        logger.debug(f"Make model simple {self.model_name}... Done")

    def compute_component_field(self, comp):
        try:
            mtd = getattr(self, f"add_{comp.get('type')}")
            mtd(comp.copy())
        except Exception as e:
            logger.error(
                f'Error creation model objec map: {comp.get("type")} \n {e}',
                exc_info=True,
            )

    def eval_component(self, comp):
        try:
            mtd = getattr(self, f"eval_{comp.get('type')}")
            mtd(comp.copy())
        except Exception as e:
            logger.error(
                f'Error Eval : {comp.get("type")} \n {e}', exc_info=True
            )

    def _scan(self, comp):
        if comp.get("type"):
            if comp.get("type") not in self.no_create_model_field_key:
                self.compute_component_field(comp.copy())
            elif comp.get("type") in self.layoyt_components:
                self.eval_component(comp.copy())

    def _make_instace(self):
        for k, v in self.instance.dict().items():
            if k in self.model_form_fields:
                if (
                    self.model_form_fields[k].type
                    not in self.no_create_model_field_key
                ):
                    component = self.model_form_fields[k]
                    self.form_fields[component.key] = copy.deepcopy(component)
                elif self.model_form_fields[k].type in self.layoyt_components:
                    component = copy.deepcopy(self.model_form_fields[k])
                    if component.childs:
                        for i in range(len(v) - 1):
                            child = copy.deepcopy(component.first_child)
                            component.childs = child
                    self.form_fields[component.key] = component

    def make(self):
        for c in self.components_todo:
            self._scan(c)
        if "rec_name" not in self.components_keys:
            component = {}
            component["type"] = "textfield"
            component["key"] = "rec_name"
            component["label"] = "Name"
            component["hidden"] = True
            component["defaultValue"] = ""
            self.compute_component_field(component.copy())

        self.make_model()


class ModelMaker(FormioModelMaker):
    pass
