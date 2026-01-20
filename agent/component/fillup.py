#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
import re
from functools import partial

from agent.component.base import ComponentParamBase, ComponentBase
from api.db.services.file_service import FileService


class UserFillUpParam(ComponentParamBase):

    def __init__(self):
        super().__init__()
        self.enable_tips = True
        self.tips = "Please fill up the form"

    def check(self) -> bool:
        return True


class UserFillUp(ComponentBase):
    component_name = "UserFillUp"

    def _invoke(self, **kwargs):
        if self.check_if_canceled("UserFillUp processing"):
            return

        if self._param.enable_tips:
            content = self._param.tips
            for k, v in self.get_input_elements_from_text(self._param.tips).items():
                v = v["value"]
                ans = ""
                if isinstance(v, partial):
                    for t in v():
                        ans += t
                elif isinstance(v, list):
                    ans = ",".join([str(vv) for vv in v])
                elif not isinstance(v, str):
                    try:
                        ans = json.dumps(v, ensure_ascii=False)
                    except Exception:
                        pass
                else:
                    ans = v
                if not ans:
                    ans = ""
                content = re.sub(r"\{%s\}"%k, ans, content)

            self.set_output("tips", content)
        for k, v in kwargs.get("inputs", {}).items():
            if self.check_if_canceled("UserFillUp processing"):
                return
            if isinstance(v, dict) and (
                v.get("type", "").lower().find("file") >= 0 or 
                v.get("type", "").lower() == "pdf"
            ):
                if v.get("optional") and v.get("value", None) is None:
                    v = None
                else:
                    pdf_parser_config = None
                    if v.get("type", "").lower() == "pdf":
                        pdf_parser_config = {}

                        if v.get("parse_method"):
                            pdf_parser_config["parse_method"] = v.get("parse_method")
                        if v.get("mineru_parse_method"):
                            pdf_parser_config["mineru_parse_method"] = v.get("mineru_parse_method")
                        if v.get("mineru_formula_enable") is not None:
                            pdf_parser_config["mineru_formula_enable"] = v.get("mineru_formula_enable")
                        if v.get("mineru_table_enable") is not None:
                            pdf_parser_config["mineru_table_enable"] = v.get("mineru_table_enable")
                        if v.get("mineru_lang"):
                            pdf_parser_config["mineru_lang"] = v.get("mineru_lang")

                        if v.get("tcadp_table_result_type"):
                            pdf_parser_config["tcadp_table_result_type"] = v.get("tcadp_table_result_type")
                        if v.get("tcadp_markdown_image_response_type"):
                            pdf_parser_config["tcadp_markdown_image_response_type"] = v.get("tcadp_markdown_image_response_type")

                        if v.get("lang"):
                            pdf_parser_config["lang"] = v.get("lang")

                        if v.get("chunk_token_num") is not None:
                            pdf_parser_config["chunk_token_num"] = v.get("chunk_token_num")
                        if v.get("delimiter"):
                            pdf_parser_config["delimiter"] = v.get("delimiter")
                        if v.get("enable_children") is not None:
                            pdf_parser_config["enable_children"] = v.get("enable_children")
                        if v.get("children_delimiter"):
                            pdf_parser_config["children_delimiter"] = v.get("children_delimiter")

                        if not pdf_parser_config:
                            pdf_parser_config = None
                    
                    v = FileService.get_files([v["value"]], pdf_parser_config)
            else:
                v = v.get("value")
            self.set_output(k, v)

    def thoughts(self) -> str:
        return "Waiting for your input..."
