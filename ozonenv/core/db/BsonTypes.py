# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

import bson
import bson.decimal128
# from pydantic.datetime_parse import parse_datetime
from pydantic_core import PydanticCustomError, core_schema
from typing import Any
from pydantic import (
    BaseModel,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    ValidationError,
)
import datetime
from pydantic.json_schema import JsonSchemaValue
from bson.objectid import ObjectId as BsonObjectId
import json


class PyObjectId(BsonObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
            cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
        )

    @classmethod
    def validate(cls, v):
        if isinstance(v, (BsonObjectId, cls)):
            return v
        if isinstance(v, str) and BsonObjectId.is_valid(v):
            return v
        raise PydanticCustomError("invalid ObjectId specified")

    @classmethod
    def __get_pydantic_json_schema__(
            cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(schema)
        json_schema.update(type="string")
        return json_schema


# Codec


class JsonEncoder(json.JSONEncoder):
    """JSON serializer for objects not serializable by default json code"""

    def default(self, o):
        if isinstance(o, bson.decimal128.Decimal128):
            return float(o.to_decimal())
        if isinstance(o, bson.objectid.ObjectId):
            return str(o)
        if isinstance(o, (datetime.datetime, datetime.date, datetime.time)):
            return o.isoformat()
        elif isinstance(o, timedelta):
            return (datetime.datetime.min + o).time().isoformat()
        return super().default(o)


BSON_TYPES_ENCODERS = {
    bson.ObjectId: str,
    bson.decimal128.Decimal128: lambda x: float(x.to_decimal()),
    # Convert to regular decimal
    bson.regex.Regex: lambda x: x.pattern,
}
