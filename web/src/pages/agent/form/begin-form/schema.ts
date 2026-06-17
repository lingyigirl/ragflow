import { WebhookJWTAlgorithmList } from '@/constants/agent';
import { z } from 'zod';

const FieldTypeSchema = z.enum([
  'line',
  'paragraph',
  'integer',
  'boolean',
  'options',
  'file',
  'pdf',
]);

export const BeginFormSchema = z.object({
  enablePrologue: z.boolean().optional(),
  prologue: z.string().trim().optional(),
  mode: z.string(),
  inputs: z
    .array(
      z.object({
        key: z.string(),
        type: FieldTypeSchema,
        value: z.union([z.string(), z.record(z.any()), z.array(z.any())]),
        optional: z.boolean(),
        name: z.string(),
        options: z.array(z.union([z.number(), z.string(), z.boolean()])),
        parse_method: z.string().optional(),

        mineru_backend: z
          .enum(['pipeline', 'vlm-vllm-async-engine', 'hybrid-auto-engine'])
          .optional(),
        mineru_parse_method: z.enum(['auto', 'txt', 'ocr']).optional(),
        mineru_formula_enable: z.boolean().optional(),
        mineru_table_enable: z.boolean().optional(),
        mineru_lang: z.string().optional(),

        tcadp_table_result_type: z.string().optional(),
        tcadp_markdown_image_response_type: z.string().optional(),

        lang: z.string().optional(),

        chunk_token_num: z.number().optional(),
        delimiter: z.string().optional(),
        enable_children: z.boolean().optional(),
        children_delimiter: z.string().optional(),
      }),
    )
    .optional(),
  param_chinese_name: z.string().optional(),
  param_english_name: z.string().optional(),
  param_default_value: z.string().optional(),
  param_type: z.enum(['string', 'file']).optional(),
  methods: z.array(z.string()).optional(),
  content_types: z.string().optional(),
  security: z
    .object({
      auth_type: z.string(),
      ip_whitelist: z.array(z.object({ value: z.string() })),
      rate_limit: z.object({
        limit: z.number(),
        per: z.string().optional(),
      }),
      max_body_size: z.string(),
      jwt: z
        .object({
          algorithm: z.string().default(WebhookJWTAlgorithmList[0]).optional(),
          required_claims: z.array(z.object({ value: z.string() })),
        })
        .optional(),
      hmac: z
        .object({
          header: z.string().optional(),
          secret: z.string().optional(),
        })
        .optional(),
    })
    .optional(),
  schema: z
    .object({
      query: z
        .array(
          z.object({
            key: z.string(),
            type: FieldTypeSchema,
            required: z.boolean(),
          }),
        )
        .optional(),
      headers: z
        .array(
          z.object({
            key: z.string(),
            type: FieldTypeSchema,
            required: z.boolean(),
          }),
        )
        .optional(),
      body: z
        .array(
          z.object({
            key: z.string(),
            type: FieldTypeSchema,
            required: z.boolean(),
          }),
        )
        .optional(),
    })
    .optional(),
  response: z
    .object({
      status: z.number(),
      body_template: z.string().optional(),
    })
    .optional(),
  execution_mode: z.string().optional(),
});

export type BeginFormSchemaType = z.infer<typeof BeginFormSchema>;
