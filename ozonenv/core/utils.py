import base64
import tempfile
import re
import aiofiles
import aiofiles.os
import json


async def read_json_file(file_path):
    async with aiofiles.open(file_path, mode="r") as f:
        data = await f.read()
    return json.loads(data)


def base64_encode_url(url):
    content = httpx.get(url).content
    tf = tempfile.TemporaryFile()
    tf.write(content)
    tf.seek(0)
    b64encode = base64.b64encode(tf.read())
    tf.close()
    # prefix and decode bytes to str
    b64encode = "%s,%s" % ("data:image/png;base64", b64encode.decode())
    return b64encode


def decode_resource_template(tmp):
    res = re.sub(r"<.*?>", " ", tmp)
    strcleaned = re.sub(r"\{{ |\ }}", "", res)
    list_kyes = strcleaned.strip().split(".")
    return list_kyes[1:]


def fetch_dict_get_value(dict_src, list_keys):
    if len(list_keys) == 0:
        return
    node = list_keys[0]
    list_keys.remove(node)
    nextdict = dict_src.get(node)
    if len(list_keys) >= 1:
        return fetch_dict_get_value(nextdict, list_keys)
    else:
        return dict_src.get(node)


def is_json(str_test):
    try:
        str_test = json.loads(str_test)
    except ValueError:
        str_test = str_test.replace("'", '"')
        try:
            str_test = json.loads(str_test)
        except ValueError:
            return False
    return str_test
