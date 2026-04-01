import { RAGFlowFormItem } from '@/components/ragflow-form';
import { ButtonLoading } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Form } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { LLMFactory } from '@/constants/llm';
import { IModalProps } from '@/interfaces/common';
import { zodResolver } from '@hookform/resolvers/zod';
import { t } from 'i18next';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { LLMHeader } from '../../components/llm-header';

const FormSchema = z.object({
  llm_name: z.string().min(1, {
    message: t('setting.mineru.modelNameRequired'),
  }),
  mineru_apiserver: z.string().url(),
  mineru_output_dir: z.string().optional(),
  mineru_server_url: z.union([z.string().url(), z.literal('')]).optional(),
  mineru_delete_output: z.boolean(),
});

export type MinerUFormValues = z.infer<typeof FormSchema>;

const MinerUModal = ({
  visible,
  hideModal,
  onOk,
  loading,
}: IModalProps<MinerUFormValues>) => {
  const { t } = useTranslation();

  const form = useForm<MinerUFormValues>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      mineru_delete_output: true,
      mineru_server_url: '',
    },
  });

  const handleOk = async (values: MinerUFormValues) => {
    const ret = await onOk?.(values as any);
    if (ret) {
      hideModal?.();
    }
  };

  return (
    <Dialog open={visible} onOpenChange={hideModal}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            <LLMHeader name={LLMFactory.MinerU} />
          </DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(handleOk)}
            className="space-y-6"
            id="mineru-form"
          >
            <RAGFlowFormItem
              name="llm_name"
              label={t('setting.modelName')}
              required
            >
              <Input placeholder="mineru-from-env-1" />
            </RAGFlowFormItem>
            <RAGFlowFormItem
              name="mineru_apiserver"
              label={t('setting.mineru.apiserver')}
              required
            >
              <Input placeholder="http://host.docker.internal:9987" />
            </RAGFlowFormItem>
            <RAGFlowFormItem
              name="mineru_output_dir"
              label={t('setting.mineru.outputDir')}
            >
              <Input placeholder="/tmp/mineru" />
            </RAGFlowFormItem>
            <RAGFlowFormItem
              name="mineru_server_url"
              label={t('setting.mineru.serverUrl')}
              tooltip={t(
                'setting.mineru.serverUrlKbBackendTip',
                'Optional. Used by some MinerU engines when a remote VLM server URL is required. Parsing engine (backend) is configured per knowledge base.',
              )}
            >
              <Input placeholder="http://your-vllm-server:30000" />
            </RAGFlowFormItem>
            <RAGFlowFormItem
              name="mineru_delete_output"
              label={t('setting.mineru.deleteOutput')}
              labelClassName="!mb-0"
            >
              {(field) => (
                <Switch
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            </RAGFlowFormItem>
          </form>
        </Form>
        <DialogFooter>
          <ButtonLoading type="submit" form="mineru-form" loading={loading}>
            {t('common.save', 'Save')}
          </ButtonLoading>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default MinerUModal;
