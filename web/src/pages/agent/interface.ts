import { RAGFlowNodeType } from '@/interfaces/database/flow';
import { FormInstance } from 'antd';

export interface IOperatorForm {
  onValuesChange?(changedValues: any, values: any): void;
  form?: FormInstance;
  node?: RAGFlowNodeType;
  nodeId?: string;
}

export interface INextOperatorForm {
  node?: RAGFlowNodeType;
  nodeId?: string;
}

export interface IGenerateParameter {
  id?: string;
  key: string;
  component_id?: string;
}

export interface IInvokeVariable extends IGenerateParameter {
  value?: string;
}

export type IPosition = { top: number; right: number; idx: number };

export interface BeginQuery {
  key: string;
  type: string;
  value: string;
  optional: boolean;
  name: string;
  options: (number | string | boolean)[];
  // PDF解析器相关配置
  parse_method?: string; // PDF解析方法：DeepDOC, Plain Text, MinerU, Docling, TCADP Parser, 或第三方视觉模型
  // MinerU配置
  mineru_parse_method?: 'auto' | 'txt' | 'ocr'; // MinerU解析方法
  mineru_formula_enable?: boolean; // MinerU公式识别
  mineru_table_enable?: boolean; // MinerU表格识别
  mineru_lang?: string; // MinerU语言设置
  // TCADP配置
  tcadp_table_result_type?: string; // TCADP表格返回形式：'0'=Markdown, '1'=HTML
  tcadp_markdown_image_response_type?: string; // TCADP图片返回形式：'0'=URL, '1'=Text
  // 通用配置
  lang?: string; // 通用语言设置
  // 文本分块配置（用于DeepDOC、Plain Text、Docling、TCADP Parser等）
  chunk_token_num?: number; // 建议文本块大小
  delimiter?: string; // 文本分段标识符
  enable_children?: boolean; // Child chunk are used for retrieval开关
  children_delimiter?: string; // Delimiter for text
}

export type IInputs = {
  avatar: string;
  title: string;
  inputs: Record<string, BeginQuery>;
  prologue: string;
  mode: string;
};

export type IOutputs = Record<
  string,
  {
    type?: string;
    value?: string;
  }
>;
