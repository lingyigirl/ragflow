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
import json
import logging
import os
from typing import Any, Optional

from deepdoc.parser.mineru_parser import MinerUParser


class Base:
    def __init__(self, key: str | dict, model_name: str, **kwargs):
        self.model_name = model_name

    def parse_pdf(self, filepath: str, binary=None, **kwargs) -> tuple[Any, Any]:
        raise NotImplementedError("Please implement parse_pdf!")


class MinerUOcrModel(Base, MinerUParser):
    _FACTORY_NAME = "MinerU"

    def __init__(self, key: str | dict, model_name: str, **kwargs):
        Base.__init__(self, key, model_name, **kwargs)
        raw_config = {}
        if key:
            try:
                raw_config = json.loads(key)
            except Exception:
                raw_config = {}

        # nested {"api_key": {...}} from UI
        # flat {"MINERU_*": "..."} payload auto-provisioned from env vars
        config = raw_config.get("api_key", raw_config)
        if not isinstance(config, dict):
            config = {}

        def _resolve_config(key: str, env_key: str, default=""):
            # 系统环境变量优先级最高，便于通过容器/进程环境强制覆盖配置  # 中文注释
            env_value = os.environ.get(env_key, None)  # 读取系统环境变量  # 中文注释
            if env_value not in (None, ""):  # 若环境变量有值则直接返回  # 中文注释
                return env_value  # 返回最高优先级配置  # 中文注释
            # 其次读取配置中的大写键（环境变量透传场景）  # 中文注释
            if env_key in config and config.get(env_key, "") != "":  # 判断大写键是否有效  # 中文注释
                return config.get(env_key)  # 返回次优先级配置  # 中文注释
            # 最后读取配置中的小写键（UI 表单场景）并回退到默认值  # 中文注释
            return config.get(key, default)  # 返回低优先级或默认值  # 中文注释

        self.mineru_api = _resolve_config("mineru_apiserver", "MINERU_APISERVER", "")
        self.mineru_output_dir = _resolve_config("mineru_output_dir", "MINERU_OUTPUT_DIR", "")
        self.mineru_backend = _resolve_config("mineru_backend", "MINERU_BACKEND", "pipeline")
        self.mineru_server_url = _resolve_config("mineru_server_url", "MINERU_SERVER_URL", "")
        self.mineru_delete_output = bool(int(_resolve_config("mineru_delete_output", "MINERU_DELETE_OUTPUT", 1)))
        self.mineru_api_key = _resolve_config("mineru_api_key", "MINERU_API_KEY", "")

        # Redact sensitive config keys before logging
        redacted_config = {}
        for k, v in config.items():
            if any(
                sensitive_word in k.lower()
                for sensitive_word in ("key", "password", "token", "secret")
            ):
                redacted_config[k] = "[REDACTED]"
            else:
                redacted_config[k] = v
        logging.info(
            f"Parsed MinerU config (sensitive fields redacted): {redacted_config}"
        )

        MinerUParser.__init__(self, mineru_api=self.mineru_api, mineru_server_url=self.mineru_server_url, mineru_api_key=self.mineru_api_key)

    def check_available(self, backend: Optional[str] = None, server_url: Optional[str] = None) -> tuple[bool, str]:
        backend = backend or self.mineru_backend
        server_url = server_url or self.mineru_server_url
        return self.check_installation(backend=backend, server_url=server_url)

    def parse_pdf(self, filepath: str, binary=None, callback=None, parse_method: str = "raw", **kwargs):
        ok, reason = self.check_available()
        if not ok:
            raise RuntimeError(f"MinerU server not accessible: {reason}")

        sections, tables = MinerUParser.parse_pdf(
            self,
            filepath=filepath,
            binary=binary,
            callback=callback,
            output_dir=self.mineru_output_dir,
            backend=self.mineru_backend,
            server_url=self.mineru_server_url,
            delete_output=self.mineru_delete_output,
            parse_method=parse_method,
            **kwargs
        )
        return sections, tables
