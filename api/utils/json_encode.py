#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import datetime
import json
import re
from enum import Enum, IntEnum
from api.utils.common import string_to_bytes, bytes_to_string

# 识别 JSON 风格的 \\uXXXX 转义片段
_UNICODE_ESCAPE_FRAGMENT_RE = re.compile(r"\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}")


def unicode_unescape_text(text):
    """将误存为 \\uXXXX 字面量的字符串还原为可读文本；正常中文/英文原样返回。"""
    if not isinstance(text, str) or not text:
        return text
    if not _UNICODE_ESCAPE_FRAGMENT_RE.search(text):
        return text
    try:
        return text.encode("utf-8").decode("unicode_escape")
    except (UnicodeError, UnicodeDecodeError):
        return text


def unicode_unescape_text_fields(obj):
    """递归还原 JSON 字段中误存的 \\uXXXX 字面量文本。"""
    if isinstance(obj, str):
        return unicode_unescape_text(obj)
    if isinstance(obj, dict):
        restored = {}
        for key, value in obj.items():
            restored_key = unicode_unescape_text(key) if isinstance(key, str) else key
            restored[restored_key] = unicode_unescape_text_fields(value)
        return restored
    if isinstance(obj, list):
        return [unicode_unescape_text_fields(item) for item in obj]
    return obj


def normalize_parent_chain_for_storage(chain):
    """写入 parent_chain 前确保为可读中文/英文，而非 \\uXXXX 字面量。"""
    if not chain:
        return chain
    if not isinstance(chain, list):
        return chain
    return [unicode_unescape_text(item) if isinstance(item, str) else item for item in chain]


class BaseType:
    def to_dict(self):
        return dict([(k.lstrip("_"), v) for k, v in self.__dict__.items()])

    def to_dict_with_type(self):
        def _dict(obj):
            module = None
            if issubclass(obj.__class__, BaseType):
                data = {}
                for attr, v in obj.__dict__.items():
                    k = attr.lstrip("_")
                    data[k] = _dict(v)
                module = obj.__module__
            elif isinstance(obj, (list, tuple)):
                data = []
                for i, vv in enumerate(obj):
                    data.append(_dict(vv))
            elif isinstance(obj, dict):
                data = {}
                for _k, vv in obj.items():
                    data[_k] = _dict(vv)
            else:
                data = obj
            return {"type": obj.__class__.__name__,
                    "data": data, "module": module}

        return _dict(self)


class CustomJSONEncoder(json.JSONEncoder):
    def __init__(self, **kwargs):
        self._with_type = kwargs.pop("with_type", False)
        super().__init__(**kwargs)

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, datetime.timedelta):
            return str(obj)
        elif issubclass(type(obj), Enum) or issubclass(type(obj), IntEnum):
            return obj.value
        elif isinstance(obj, set):
            return list(obj)
        elif issubclass(type(obj), BaseType):
            if not self._with_type:
                return obj.to_dict()
            else:
                return obj.to_dict_with_type()
        elif isinstance(obj, type):
            return obj.__name__
        else:
            return json.JSONEncoder.default(self, obj)


def json_dumps(src, byte=False, indent=None, with_type=False):
    dest = json.dumps(
        src,
        indent=indent,
        cls=CustomJSONEncoder,
        with_type=with_type,
        ensure_ascii=False,
    )
    if byte:
        dest = string_to_bytes(dest)
    return dest


def json_loads(src, object_hook=None, object_pairs_hook=None):
    if isinstance(src, bytes):
        src = bytes_to_string(src)
    return json.loads(src, object_hook=object_hook,
                      object_pairs_hook=object_pairs_hook)
