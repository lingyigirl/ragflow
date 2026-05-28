import { AgentGlobals } from '@/constants/agent';
import { useFetchAgent } from '@/hooks/use-agent-request';
import { downloadJsonFile } from '@/utils/file-util';
import { useCallback } from 'react';
import { useBuildDslData } from './use-build-dsl';

export const useHandleExportJsonFile = () => {
  const { buildDslData } = useBuildDslData();
  const { data } = useFetchAgent();

  const handleExportJson = useCallback(() => {
    const dsl = buildDslData();
    const globals = (dsl.globals ?? {}) as Record<string, string>;
    downloadJsonFile(
      {
        ...dsl.graph,
        agent_type: data.agent_type ?? globals[AgentGlobals.AgentPartyType],
        agent_type_cn:
          data.agent_type_cn ?? globals[AgentGlobals.AgentPartyTypeNameZh],
        agent_type_en:
          data.agent_type_en ?? globals[AgentGlobals.AgentPartyTypeNameEn],
      },
      `${data.title}.json`,
    );
  }, [buildDslData, data]);

  return {
    handleExportJson,
  };
};
