import { DelimiterInput } from '@/components/delimiter-form-field';
import { KeyInput } from '@/components/key-input';
import { LayoutRecognizeFormField } from '@/components/layout-recognize-form-field';
import { MINERU_KB_BACKEND_VALUES } from '@/components/mineru-options-form-field';
import { SliderInputFormField } from '@/components/slider-input-form-field';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { RAGFlowSelect, RAGFlowSelectOptionType } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { FormLayout } from '@/constants/form';
import { useTranslate } from '@/hooks/common-hooks';
import { IModalProps } from '@/interfaces/common';
import { zodResolver } from '@hookform/resolvers/zod';
import { isEmpty } from 'lodash';
import { ChangeEvent, useEffect, useMemo } from 'react';
import { useForm, useFormContext, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { BeginQueryType, BeginQueryTypeIconMap } from '../../constant';
import { BeginQuery } from '../../interface';
import { BeginDynamicOptions } from './begin-dynamic-options';

type ModalFormProps = {
  initialValue: BeginQuery;
  otherThanCurrentQuery: BeginQuery[];
  submit(values: any): void;
};

const FormId = 'BeginParameterForm';

function ParameterForm({
  initialValue,
  otherThanCurrentQuery,
  submit,
}: ModalFormProps) {
  const { t } = useTranslate('flow');
  const FormSchema = z.object({
    type: z.string(),
    key: z
      .string()
      .trim()
      .min(1)
      .refine(
        (value) =>
          !value || !otherThanCurrentQuery.some((x) => x.key === value),
        { message: 'The key cannot be repeated!' },
      ),
    optional: z.boolean(),
    name: z.string().trim().min(1),
    options: z
      .array(z.object({ value: z.string().or(z.boolean()).or(z.number()) }))
      .optional(),
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
  });

  const form = useForm<z.infer<typeof FormSchema>>({
    resolver: zodResolver(FormSchema),
    mode: 'onChange',
    defaultValues: {
      type: BeginQueryType.Line,
      optional: false,
      key: '',
      name: '',
      options: [],
    },
  });

  const options = useMemo(() => {
    return Object.values(BeginQueryType).reduce<RAGFlowSelectOptionType[]>(
      (pre, cur) => {
        const Icon = BeginQueryTypeIconMap[cur];

        return [
          ...pre,
          {
            label: (
              <div className="flex items-center gap-2">
                <Icon
                  className={`size-${cur === BeginQueryType.Options ? 4 : 5}`}
                ></Icon>
                {t(cur.toLowerCase())}
              </div>
            ),
            value: cur,
          },
        ];
      },
      [],
    );
  }, []);

  const type = useWatch({
    control: form.control,
    name: 'type',
  });

  useEffect(() => {
    if (!isEmpty(initialValue)) {
      form.reset({
        ...initialValue,
        options: initialValue.options?.map((x) => ({ value: x })),

        parse_method: initialValue.parse_method || undefined,
        mineru_backend: initialValue.mineru_backend || undefined,
        mineru_parse_method: initialValue.mineru_parse_method || undefined,
        mineru_formula_enable: initialValue.mineru_formula_enable ?? undefined,
        mineru_table_enable: initialValue.mineru_table_enable ?? undefined,
        mineru_lang: initialValue.mineru_lang || undefined,
        tcadp_table_result_type:
          (initialValue as any).tcadp_table_result_type || undefined,
        tcadp_markdown_image_response_type:
          (initialValue as any).tcadp_markdown_image_response_type || undefined,
        lang: initialValue.lang || undefined,
        chunk_token_num: (initialValue as any).chunk_token_num ?? undefined,
        delimiter: (initialValue as any).delimiter || undefined,
        enable_children: (initialValue as any).enable_children ?? undefined,
        children_delimiter:
          (initialValue as any).children_delimiter || undefined,
      });
    }
  }, [form, initialValue]);

  function onSubmit(data: z.infer<typeof FormSchema>) {
    const values = { ...data, options: data.options?.map((x) => x.value) };

    submit(values);
  }

  const handleKeyChange = (e: ChangeEvent<HTMLInputElement>) => {
    const name = form.getValues().name || '';
    form.setValue('key', e.target.value.trim());
    if (!name) {
      form.setValue('name', e.target.value.trim());
    }
  };
  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        id={FormId}
        className="space-y-5"
        autoComplete="off"
      >
        <FormField
          name="type"
          control={form.control}
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('type')}</FormLabel>
              <FormControl>
                <RAGFlowSelect {...field} options={options} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          name="key"
          control={form.control}
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('key')}</FormLabel>
              <FormControl>
                <KeyInput
                  {...field}
                  autoComplete="off"
                  onBlur={handleKeyChange}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          name="name"
          control={form.control}
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('name')}</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          name="optional"
          control={form.control}
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('optional')}</FormLabel>
              <FormControl>
                <Switch
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {type === BeginQueryType.Options && (
          <BeginDynamicOptions></BeginDynamicOptions>
        )}
        {}
        {type === BeginQueryType.PDF && <BeginPdfParserOptions />}
      </form>
    </Form>
  );
}

function BeginTextChunkingConfig() {
  const { t } = useTranslation();
  const form = useFormContext();
  const enableChildren = useWatch({
    control: form.control,
    name: 'enable_children',
  });
  const childrenDelimiterValue = useWatch({
    control: form.control,
    name: 'children_delimiter',
  });

  useEffect(() => {
    if (typeof form.getValues('chunk_token_num') === 'undefined') {
      form.setValue('chunk_token_num', 512, {
        shouldValidate: true,
        shouldDirty: true,
      });
    }
    if (typeof form.getValues('delimiter') === 'undefined') {
      form.setValue('delimiter', '\n', {
        shouldValidate: true,
        shouldDirty: true,
      });
    }
  }, [form]);

  return (
    <div className="space-y-4 border-t pt-4 mt-4">
      <div className="text-sm font-medium text-text-secondary">
        {t('knowledgeConfiguration.textChunking', '文本分块配置')}
      </div>
      {}
      <SliderInputFormField
        name="chunk_token_num"
        label={t('knowledgeConfiguration.chunkTokenNumber', '建议文本块大小')}
        tooltip={t(
          'knowledgeConfiguration.chunkTokenNumberTip',
          '设置创建块的token阈值。少于该阈值的段落将与后续段落合并，直到token数超过阈值，此时创建一个块。除非遇到分隔符，否则即使超过阈值也不会创建新块。',
        )}
        max={2048}
        min={1}
        defaultValue={512}
        layout={FormLayout.Vertical}
      />
      {}
      <FormField
        control={form.control}
        name="delimiter"
        render={({ field }) => (
          <FormItem>
            <FormLabel
              required
              tooltip={t(
                'knowledgeDetails.delimiterTip',
                '支持多字符作为分隔符，多字符用两个反引号 `` 分隔符包裹。若配置成：\\n`##`; 系统将首先使用换行符、两个#号以及分号先对文本进行分割，随后再对分得的小文本块按照「建议文本块大小」设定的大小进行拼装。',
              )}
            >
              {t('knowledgeDetails.delimiter', '文本分段标识符')}
            </FormLabel>
            <FormControl>
              <DelimiterInput {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      {}
      <FormField
        control={form.control}
        name="enable_children"
        render={({ field: { value, onChange, ...restProps } }) => (
          <FormItem className="items-center space-y-0">
            <div className="flex items-center justify-between gap-1">
              <FormLabel>
                {t(
                  'knowledgeDetails.enableChildrenDelimiter',
                  'Child chunk are used for retrieval',
                )}
              </FormLabel>
              <div className="flex-none">
                <FormControl>
                  <Switch
                    checked={value ?? false}
                    onCheckedChange={(checked) => {
                      if (checked && !childrenDelimiterValue) {
                        form.setValue('children_delimiter', '\n', {
                          shouldValidate: true,
                          shouldDirty: true,
                        });
                      }
                      onChange(checked);
                    }}
                    {...restProps}
                  />
                </FormControl>
              </div>
            </div>
          </FormItem>
        )}
      />
      {}
      {enableChildren && (
        <FormField
          control={form.control}
          name="children_delimiter"
          render={({ field }) => (
            <FormItem>
              <FormLabel
                required
                tooltip={t(
                  'knowledgeDetails.childrenDelimiterTip',
                  '支持多字符作为分隔符，多字符用两个反引号 `` 分隔符包裹。',
                )}
              >
                {t('knowledgeDetails.childrenDelimiter', 'Delimiter for text')}
              </FormLabel>
              <FormControl>
                <DelimiterInput {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      )}
    </div>
  );
}

function BeginPdfParserOptions() {
  const { t } = useTranslation();
  const form = useFormContext();
  const parseMethod = useWatch({
    control: form.control,
    name: 'parse_method',
  });

  const parserType = useMemo(() => {
    if (!parseMethod) return null;
    const lower = parseMethod.toLowerCase();
    if (lower.includes('mineru')) return 'mineru';
    if (lower === 'deepdoc') return 'deepdoc';
    if (lower === 'plain text' || lower === 'plaintext') return 'plaintext';
    if (lower === 'docling') return 'docling';
    if (lower === 'tcadp parser' || lower === 'tcadp') return 'tcadp';
    return 'other';
  }, [parseMethod]);

  useEffect(() => {
    if (!parseMethod) {
      form.setValue('parse_method', 'DeepDOC', {
        shouldValidate: true,
        shouldDirty: true,
      });
    }
  }, [form, parseMethod]);

  useEffect(() => {
    if (parserType === 'mineru') {
      if (!form.getValues('mineru_backend')) {
        form.setValue('mineru_backend', 'pipeline', {
          shouldValidate: true,
          shouldDirty: true,
        });
      }
      if (!form.getValues('mineru_parse_method')) {
        form.setValue('mineru_parse_method', 'auto', {
          shouldValidate: true,
          shouldDirty: true,
        });
      }
      if (!form.getValues('mineru_lang')) {
        form.setValue('mineru_lang', 'Chinese', {
          shouldValidate: true,
          shouldDirty: true,
        });
      }
      if (typeof form.getValues('mineru_formula_enable') === 'undefined') {
        form.setValue('mineru_formula_enable', true, {
          shouldValidate: true,
          shouldDirty: true,
        });
      }
      if (typeof form.getValues('mineru_table_enable') === 'undefined') {
        form.setValue('mineru_table_enable', true, {
          shouldValidate: true,
          shouldDirty: true,
        });
      }
    }
  }, [form, parserType]);

  return (
    <div className="space-y-4 border-t pt-4 mt-4">
      <div className="text-sm font-medium text-text-secondary">
        {t('flow.pdfParser', 'PDF解析器')}
      </div>
      <LayoutRecognizeFormField
        name="parse_method"
        horizontal={false}
        label={t('flow.parserMethod', '解析方法')}
        showMineruOptions={false}
      />

      {}
      {parserType && (
        <div className="max-h-[60vh] overflow-y-auto border rounded-md p-4 space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-text-primary pb-2 border-b mb-2">
            {}
            <span className="w-1 h-3 bg-primary rounded-full"></span>
            {t('flow.parserConfig', '解析器配置')}
          </div>
          {}
          {(parserType === 'deepdoc' ||
            parserType === 'plaintext' ||
            parserType === 'docling') && (
            <div className="space-y-4">
              {}
              <BeginTextChunkingConfig />
            </div>
          )}

          {}
          {parserType === 'mineru' && (
            <div className="mt-6 space-y-6">
              {' '}
              {}
              {}
              <div className="relative flex items-center py-2">
                <div className="flex-grow border-t border-primary/30"></div>
                <span className="flex-shrink mx-4 text-sm font-semibold text-primary uppercase tracking-wider">
                  {t('knowledgeConfiguration.mineruOptions', 'MinerU 选项')}
                </span>
                <div className="flex-grow border-t border-primary/30"></div>
              </div>
              <div className="grid gap-5 pl-2">
                {}
                <FormField
                  control={form.control}
                  name="mineru_backend"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel
                        tooltip={t(
                          'knowledgeConfiguration.mineruBackendTip',
                          'MinerU PDF 解析引擎',
                        )}
                      >
                        {t(
                          'knowledgeConfiguration.mineruBackend',
                          'MinerU backend',
                        )}
                      </FormLabel>
                      <FormControl>
                        <RAGFlowSelect
                          value={field.value || 'pipeline'}
                          onChange={field.onChange}
                          options={MINERU_KB_BACKEND_VALUES.map((v) => ({
                            label: v,
                            value: v,
                          }))}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="mineru_parse_method"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel
                        tooltip={t(
                          'knowledgeConfiguration.mineruParseMethodTip',
                          '解析方法：auto（自动检测）、txt（文本提取）、ocr（光学字符识别）',
                        )}
                      >
                        {t(
                          'knowledgeConfiguration.mineruParseMethod',
                          '解析方法',
                        )}
                      </FormLabel>
                      <FormControl>
                        <RAGFlowSelect
                          value={field.value || 'auto'}
                          onChange={field.onChange}
                          options={[
                            { label: 'Auto', value: 'auto' },
                            { label: 'Text', value: 'txt' },
                            { label: 'OCR', value: 'ocr' },
                          ]}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {}
                <FormField
                  control={form.control}
                  name="mineru_lang"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel
                        tooltip={t(
                          'knowledgeConfiguration.mineruLanguageTip',
                          'MinerU的首选OCR语言',
                        )}
                      >
                        {t('knowledgeConfiguration.mineruLanguage', 'Language')}
                      </FormLabel>
                      <FormControl>
                        <RAGFlowSelect
                          value={field.value || 'Chinese'}
                          onChange={field.onChange}
                          options={[
                            { label: 'English', value: 'English' },
                            { label: 'Chinese', value: 'Chinese' },
                            {
                              label: 'Traditional Chinese',
                              value: 'Traditional Chinese',
                            },
                            { label: 'Russian', value: 'Russian' },
                            { label: 'Ukrainian', value: 'Ukrainian' },
                            { label: 'Indonesian', value: 'Indonesian' },
                            { label: 'Spanish', value: 'Spanish' },
                            { label: 'Vietnamese', value: 'Vietnamese' },
                            { label: 'Japanese', value: 'Japanese' },
                            { label: 'Korean', value: 'Korean' },
                            { label: 'Portuguese BR', value: 'Portuguese BR' },
                            { label: 'German', value: 'German' },
                            { label: 'French', value: 'French' },
                            { label: 'Italian', value: 'Italian' },
                            { label: 'Tamil', value: 'Tamil' },
                            { label: 'Telugu', value: 'Telugu' },
                            { label: 'Kannada', value: 'Kannada' },
                            { label: 'Thai', value: 'Thai' },
                            { label: 'Greek', value: 'Greek' },
                            { label: 'Hindi', value: 'Hindi' },
                          ]}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {}
                <div className="space-y-3 pt-2">
                  {}
                  <FormField
                    control={form.control}
                    name="mineru_formula_enable"
                    render={({ field: { value, onChange, ...restProps } }) => (
                      <FormItem className="flex items-center justify-between rounded-lg border p-3 shadow-sm">
                        <FormLabel
                          className="cursor-pointer"
                          tooltip={t(
                            'knowledgeConfiguration.mineruFormulaEnableTip',
                            '启用公式识别。注意：对于西里尔文文档可能无法正常工作',
                          )}
                        >
                          {t(
                            'knowledgeConfiguration.mineruFormulaEnable',
                            '公式识别',
                          )}
                        </FormLabel>
                        <FormControl>
                          <Switch
                            checked={value ?? true}
                            onCheckedChange={onChange}
                            {...restProps}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />

                  {}
                  <FormField
                    control={form.control}
                    name="mineru_table_enable"
                    render={({ field: { value, onChange, ...restProps } }) => (
                      <FormItem className="flex items-center justify-between rounded-lg border p-3 shadow-sm">
                        <FormLabel
                          className="cursor-pointer"
                          tooltip={t(
                            'knowledgeConfiguration.mineruTableEnableTip',
                            '启用表格识别和提取',
                          )}
                        >
                          {t(
                            'knowledgeConfiguration.mineruTableEnable',
                            '表格识别',
                          )}
                        </FormLabel>
                        <FormControl>
                          <Switch
                            checked={value ?? true}
                            onCheckedChange={onChange}
                            {...restProps}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </div>

                {}
                <div className="mt-2">
                  <BeginTextChunkingConfig />
                </div>
              </div>
            </div>
          )}

          {}
          {parserType === 'tcadp' && (
            <div className="space-y-4">
              <FormField
                control={form.control}
                name="tcadp_table_result_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel
                      tooltip={t(
                        'flow.tableResultTypeTip',
                        '表格返回形式：Markdown或HTML',
                      )}
                    >
                      {t('flow.tableResultType', '表格返回形式')}
                    </FormLabel>
                    <FormControl>
                      <RAGFlowSelect
                        value={field.value || '1'}
                        onChange={field.onChange}
                        options={[
                          { label: 'Markdown', value: '0' },
                          { label: 'HTML', value: '1' },
                        ]}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <BeginTextChunkingConfig />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ParameterDialog({
  initialValue,
  hideModal,
  otherThanCurrentQuery,
  submit,
}: ModalFormProps & IModalProps<BeginQuery>) {
  const { t } = useTranslation();

  return (
    <Dialog open onOpenChange={hideModal}>
      <DialogContent className="flex flex-col max-h-[85vh]">
        <DialogHeader>
          <DialogTitle>{t('flow.variableSettings')}</DialogTitle>
        </DialogHeader>

        {}
        <div className="flex-1 overflow-y-auto pr-2">
          <ParameterForm
            initialValue={initialValue}
            otherThanCurrentQuery={otherThanCurrentQuery}
            submit={submit}
          />
        </div>

        <DialogFooter className="pt-3">
          <Button type="submit" form={FormId}>
            {t('modal.okText')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
