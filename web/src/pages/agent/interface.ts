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
  parse_method?: string;
  mineru_backend?: 'pipeline' | 'vlm-vllm-async-engine' | 'hybrid-auto-engine';
  mineru_parse_method?: 'auto' | 'txt' | 'ocr'; 
  mineru_formula_enable?: boolean; 
  mineru_table_enable?: boolean; 
  mineru_lang?: string; 
  tcadp_table_result_type?: string; 
  tcadp_markdown_image_response_type?: string; 
  lang?: string; 
  chunk_token_num?: number; 
  delimiter?: string; 
  enable_children?: boolean; 
  children_delimiter?: string; 
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
