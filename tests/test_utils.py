import os
import logging
import json
import aiofiles
import aiofiles.os
from aiofiles.os import wrap

upload_folder = "uploads"


def get_config_path():
    cwd = os.path.dirname(os.path.realpath(__file__))
    path = '%s/%s/%s' % (cwd, "data", "config.json")
    return path


async def readfilejson(dir_path, filename):
    cwd = os.path.dirname(os.path.realpath(__file__))
    path = '%s/%s/%s' % (cwd, dir_path, filename)
    async with aiofiles.open(path, mode='r') as f:
        data = await f.read()
    return json.loads(data)


async def readfile(upload_path, fileurl):
    cwd = os.path.dirname(os.path.realpath(__file__))
    path = f'{cwd}/{upload_path}/{fileurl}'
    async with aiofiles.open(path, mode='r') as f:
        return await f.read()


DOC_TYPES = [
    {
        "label": "Ordine",
        "value": "ordine"
    },
    {
        "label": "Fattura",
        "value": "fattura"
    },
    {
        "label": "Incarico",
        "value": "incarico"
    },
    {
        "label": "Rda contante",
        "value": "rda_contante"
    },
    {
        "label": "Rda Carta Credito",
        "value": "rda_cc"
    },
    {
        "label": "Commessa",
        "value": "commessa"
    },
    {
        "label": "Rda",
        "value": "rda"
    },
    {
        "label": "Reso",
        "value": "reso"
    }
]
