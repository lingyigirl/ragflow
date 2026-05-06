import { useFormContext, useWatch } from 'react-hook-form';

import PageRankFormField from '@/components/page-rank-form-field';
import { DocumentParserType } from '@/constants/knowledge';
import { useMemo } from 'react';
import { AudioConfiguration } from './configuration/audio';
import { BookConfiguration } from './configuration/book';
import {
  ChunkMethodItem,
  EmbeddingModelItem,
} from './configuration/common-item';
import { EmailConfiguration } from './configuration/email';
import { KnowledgeGraphConfiguration } from './configuration/knowledge-graph';
import { LawsConfiguration } from './configuration/laws';
import { ManualConfiguration } from './configuration/manual';
import { NaiveConfiguration } from './configuration/naive';
import { OneConfiguration } from './configuration/one';
import { PaperConfiguration } from './configuration/paper';
import { PictureConfiguration } from './configuration/picture';
import { PresentationConfiguration } from './configuration/presentation';
import { QAConfiguration } from './configuration/qa';
import { ResumeConfiguration } from './configuration/resume';
import { TableConfiguration } from './configuration/table';
import { TagConfiguration } from './configuration/tag';

function HichunkConfiguration() {
  return (
    <section className="relative isolate overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-muted/40 via-background to-muted/30 px-5 py-6 shadow-sm ring-1 ring-black/[0.03] dark:ring-white/[0.06]">
      <div
        aria-hidden
        className="pointer-events-none absolute -right-16 -top-24 h-56 w-56 rounded-full bg-primary/[0.07] blur-3xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-20 -left-12 h-48 w-48 rounded-full bg-emerald-500/[0.06] blur-3xl"
      />
      <div className="relative space-y-6">
        <header className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
            HiChunk
          </p>
          <h3 className="text-lg font-semibold tracking-tight text-foreground">
            文档解析与分块
          </h3>
          <p className="max-w-prose text-sm leading-relaxed text-muted-foreground">
            接入嵌入模型、内置切片策略与
            PageRank，保持与知识库其他配置一致的层级与间距。
          </p>
        </header>
        <div className="space-y-5 rounded-xl border border-border/50 bg-background/80 p-4 backdrop-blur-sm">
          <EmbeddingModelItem></EmbeddingModelItem>
          <ChunkMethodItem></ChunkMethodItem>
          <PageRankFormField />
        </div>
      </div>
    </section>
  );
}

const ConfigurationComponentMap = {
  [DocumentParserType.Naive]: NaiveConfiguration,
  [DocumentParserType.Qa]: QAConfiguration,
  [DocumentParserType.Resume]: ResumeConfiguration,
  [DocumentParserType.Manual]: ManualConfiguration,
  [DocumentParserType.Table]: TableConfiguration,
  [DocumentParserType.Paper]: PaperConfiguration,
  [DocumentParserType.Book]: BookConfiguration,
  [DocumentParserType.Laws]: LawsConfiguration,
  [DocumentParserType.Presentation]: PresentationConfiguration,
  [DocumentParserType.Picture]: PictureConfiguration,
  [DocumentParserType.One]: OneConfiguration,
  [DocumentParserType.Audio]: AudioConfiguration,
  [DocumentParserType.Email]: EmailConfiguration,
  [DocumentParserType.Tag]: TagConfiguration,
  [DocumentParserType.KnowledgeGraph]: KnowledgeGraphConfiguration,
  [DocumentParserType.Hichunk]: HichunkConfiguration,
};

function EmptyComponent() {
  return <div></div>;
}

export function ChunkMethodForm() {
  const form = useFormContext();

  const finalParserId: DocumentParserType = useWatch({
    control: form.control,
    name: 'parser_id',
  });

  const ConfigurationComponent = useMemo(() => {
    return finalParserId
      ? ConfigurationComponentMap[finalParserId]
      : EmptyComponent;
  }, [finalParserId]);

  return (
    <section className="h-full flex flex-col">
      <div className="overflow-auto flex-1 min-h-0">
        <ConfigurationComponent></ConfigurationComponent>
      </div>
    </section>
  );
}
