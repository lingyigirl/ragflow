import { IDocumentInfo } from '@/interfaces/database/document';
import { listDocument } from '@/services/knowledge-service';
import { useQuery } from '@tanstack/react-query';
import { FileText } from 'lucide-react';
import { useEffect, useMemo, useRef } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { FormControl, FormField, FormItem, FormLabel } from './ui/form';
import { MultiSelect, MultiSelectOptionType } from './ui/multi-select';

function useFetchDocumentsByKbIds(kbIds: string[]) {
  const { data, isFetching } = useQuery<IDocumentInfo[]>({
    queryKey: ['fetchDocumentsByKbIds', kbIds],
    initialData: [],
    enabled: kbIds.length > 0,
    queryFn: async () => {
      const results = await Promise.all(
        kbIds.map((kbId) =>
          listDocument({ kb_id: kbId, page_size: 1000, page: 1 }, {}).then(
            (res) => {
              if (res.data?.code === 0) {
                return (res.data.data?.docs ?? []) as IDocumentInfo[];
              }
              return [] as IDocumentInfo[];
            },
          ),
        ),
      );
      return results.flat();
    },
  });

  return { documents: data, loading: isFetching };
}

export function DocumentFormField() {
  const form = useFormContext();
  const { t } = useTranslation();

  const kbIds: string[] =
    useWatch({ control: form.control, name: 'kb_ids' }) ?? [];

  const { documents } = useFetchDocumentsByKbIds(kbIds);

  const validDocIds = useMemo(() => {
    return new Set(documents.map((d) => d.id));
  }, [documents]);

  const prevKbIdsRef = useRef<string[]>(kbIds);

  useEffect(() => {
    const prev = prevKbIdsRef.current;
    prevKbIdsRef.current = kbIds;

    if (JSON.stringify(prev) === JSON.stringify(kbIds)) return;

    const currentDocIds: string[] = form.getValues('document_ids') ?? [];
    if (currentDocIds.length > 0) {
      const filtered = currentDocIds.filter((id) => validDocIds.has(id));
      if (filtered.length !== currentDocIds.length) {
        form.setValue('document_ids', filtered);
      }
    }
  }, [kbIds, validDocIds, form]);

  const options: MultiSelectOptionType[] = useMemo(() => {
    return documents.map((doc) => ({
      label: doc.name,
      value: doc.id,
      icon: () => <FileText className="size-4" />,
    }));
  }, [documents]);

  if (kbIds.length === 0) {
    return null;
  }

  return (
    <FormField
      control={form.control}
      name="document_ids"
      render={({ field }) => (
        <FormItem>
          <FormLabel tooltip={t('chat.documentsTip')}>
            {t('chat.documents')}
          </FormLabel>
          <FormControl>
            <MultiSelect
              options={options}
              onValueChange={field.onChange}
              placeholder={t('chat.documentsMessage')}
              variant="inverted"
              maxCount={100}
              defaultValue={field.value ?? []}
              showSelectAll={false}
              {...field}
            />
          </FormControl>
        </FormItem>
      )}
    />
  );
}
