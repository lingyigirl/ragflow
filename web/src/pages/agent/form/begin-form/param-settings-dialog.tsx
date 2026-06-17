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
import { RAGFlowSelect } from '@/components/ui/select';
import { IModalProps } from '@/interfaces/common';
import { zodResolver } from '@hookform/resolvers/zod';
import { isEmpty } from 'lodash';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { ParamSetting } from '../../interface';

type ModalFormProps = {
  initialValue: ParamSetting;
  submit(values: ParamSetting): void;
};

const FormId = 'ParamSettingForm';

const ParamTypeOptions = [
  { value: 'string', label: '字符串' },
  { value: 'file', label: '文件' },
];

function ParamSettingForm({ initialValue, submit }: ModalFormProps) {
  const FormSchema = z.object({
    name_cn: z.string().trim().min(1),
    name_en: z.string().trim().min(1),
    default_value: z.string().optional(),
    param_type: z.string(),
  });

  const form = useForm<z.infer<typeof FormSchema>>({
    resolver: zodResolver(FormSchema),
    mode: 'onChange',
    defaultValues: {
      name_cn: '',
      name_en: '',
      default_value: '',
      param_type: 'string',
    },
  });

  useEffect(() => {
    if (!isEmpty(initialValue)) {
      form.reset({
        name_cn: initialValue.name_cn || '',
        name_en: initialValue.name_en || '',
        default_value: initialValue.default_value || '',
        param_type: initialValue.param_type || 'string',
      });
    }
  }, [form, initialValue]);

  function onSubmit(data: z.infer<typeof FormSchema>) {
    submit(data as ParamSetting);
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        id={FormId}
        className="space-y-5"
        autoComplete="off"
      >
        <FormField
          name="name_cn"
          control={form.control}
          render={({ field }) => (
            <FormItem>
              <FormLabel>参数中文名称</FormLabel>
              <FormControl>
                <Input {...field} placeholder="请输入参数中文名称" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          name="name_en"
          control={form.control}
          render={({ field }) => (
            <FormItem>
              <FormLabel>参数英文名称</FormLabel>
              <FormControl>
                <Input {...field} placeholder="请输入参数英文名称" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          name="default_value"
          control={form.control}
          render={({ field }) => (
            <FormItem>
              <FormLabel>参数默认值</FormLabel>
              <FormControl>
                <Input {...field} placeholder="请输入参数默认值" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          name="param_type"
          control={form.control}
          render={({ field }) => (
            <FormItem>
              <FormLabel>参数类型</FormLabel>
              <FormControl>
                <RAGFlowSelect
                  placeholder="请选择参数类型"
                  options={ParamTypeOptions}
                  {...field}
                ></RAGFlowSelect>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </form>
    </Form>
  );
}

export function ParamSettingsDialog({
  initialValue,
  hideModal,
  submit,
}: ModalFormProps & IModalProps<ParamSetting>) {
  const { t } = useTranslation();

  return (
    <Dialog open onOpenChange={hideModal}>
      <DialogContent className="flex flex-col max-h-[85vh]">
        <DialogHeader>
          <DialogTitle>参数设置</DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto pr-2">
          <ParamSettingForm initialValue={initialValue} submit={submit} />
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
