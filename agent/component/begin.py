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
from agent.component.fillup import UserFillUpParam, UserFillUp
from api.db.services.file_service import FileService


class BeginParam(UserFillUpParam):

    """
    Define the Begin component parameters.
    """
    def __init__(self):
        super().__init__()
        self.mode = "conversational"
        self.prologue = "Hi! I'm your smart assistant. What can I do for you?"

    def check(self):
        self.check_valid_value(self.mode, "The 'mode' should be either `conversational` or `task`", ["conversational", "task","Webhook"])

    def get_input_form(self) -> dict[str, dict]:
        return getattr(self, "inputs")


class Begin(UserFillUp):
    component_name = "Begin"

    def _invoke(self, **kwargs):
        if self.check_if_canceled("Begin processing"):
            return

        for k, v in kwargs.get("inputs", {}).items():
            if self.check_if_canceled("Begin processing"):
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
                    
                    # 支持多个文件：如果 value 是数组，直接使用；如果是单个对象，包装成数组
                    file_value = v["value"]
                    if isinstance(file_value, list):
                        # 已经是数组，直接使用
                        file_list = file_value
                    else:
                        # 单个文件对象，包装成数组
                        file_list = [file_value]
                    
                    # 解析所有文件，返回字符串列表
                    parsed_results = FileService.get_files(file_list, pdf_parser_config)
                    
                    # 将多个文件的解析结果合并成一个字符串，用双换行符分隔
                    # 这样 Message 节点可以正确显示所有文件的内容
                    if len(parsed_results) == 1:
                        v = parsed_results[0]
                    elif len(parsed_results) > 1:
                        # 合并所有文件的解析结果
                        v = "\n\n".join(parsed_results)
                    else:
                        v = ""

            self.set_output(k, v)
            self.set_input_value(k, v)

    def thoughts(self) -> str:
        return ""
