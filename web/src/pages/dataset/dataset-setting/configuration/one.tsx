import {
  AutoKeywordsFormField,
  AutoQuestionsFormField,
} from '@/components/auto-keywords-form-field';
import { LayoutRecognizeFormField } from '@/components/layout-recognize-form-field';
import { ConfigurationFormContainer } from '../configuration-form-container';
import { AutoMetadata } from './common-item';

export function OneConfiguration() {
  return (
    <section className="relative isolate overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-amber-500/[0.04] via-background to-slate-500/[0.05] px-5 py-6 shadow-sm ring-1 ring-black/[0.03] dark:from-amber-500/[0.06] dark:to-slate-900/40 dark:ring-white/[0.06]">
      <div
        aria-hidden
        className="pointer-events-none absolute -left-20 top-0 h-52 w-52 rounded-full bg-amber-500/[0.12] blur-3xl dark:bg-amber-400/[0.08]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-16 right-0 h-44 w-44 rounded-full bg-sky-500/[0.08] blur-3xl"
      />
      <div className="relative space-y-6">
        <header className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-muted-foreground">
            One
          </p>
          <h3 className="text-lg font-semibold tracking-tight text-foreground">
            整篇一体化
          </h3>
          <p className="max-w-prose text-sm leading-relaxed text-muted-foreground">
            优先经 MinerU 解析
            PDF、表格与图片后合并为单块；其他类型将走稳定回退解析。请在此选择布局识别，并配置元数据与自动关键词、问题。
          </p>
        </header>
        <div className="rounded-xl border border-border/50 bg-background/85 p-4 shadow-[0_1px_0_rgba(0,0,0,0.04)] backdrop-blur-sm dark:bg-background/60 dark:shadow-[0_1px_0_rgba(255,255,255,0.04)]">
          <ConfigurationFormContainer className="space-y-5">
            <LayoutRecognizeFormField />
            <AutoMetadata />
            <AutoKeywordsFormField />
            <AutoQuestionsFormField />
          </ConfigurationFormContainer>
        </div>
      </div>
    </section>
  );
}
