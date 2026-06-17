import { RAGFlowNodeType } from '@/interfaces/database/flow';
import { isEmpty } from 'lodash';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { AgentDialogueMode } from '../../constant';
import { buildBeginInputListFromObject } from './utils';

export function useValues(node?: RAGFlowNodeType) {
  const { t } = useTranslation();

  const defaultValues = useMemo(
    () => ({
      enablePrologue: true,
      prologue: t('chat.setAnOpenerInitial'),
      mode: AgentDialogueMode.Conversational,
      inputs: [],
      param_chinese_name: '',
      param_english_name: '',
      param_default_value: '',
      param_type: 'string',
    }),
    [t],
  );

  const values = useMemo(() => {
    const formData = node?.data?.form;

    if (isEmpty(formData)) {
      return defaultValues;
    }

    const inputs = buildBeginInputListFromObject(formData?.inputs);

    return { ...(formData || {}), inputs };
  }, [defaultValues, node?.data?.form]);

  return values;
}
