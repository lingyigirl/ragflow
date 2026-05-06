import { FilterCollection } from '@/components/list-filter-bar/interface';
import { IFlow } from '@/interfaces/database/agent';
import { useFetchAgentList } from '@/hooks/use-agent-request';
import {
  FilterType,
  buildOwnersFilter,
  groupListByType,
} from '@/utils/list-filter-util';
import { useMemo } from 'react';

function bucketAgentType(raw: unknown): 'none' | 'personal' | 'enterprise' {
  if (raw == null || raw === '' || raw === 'none') {
    return 'none';
  }
  if (raw === 'personal') {
    return 'personal';
  }
  if (raw === 'enterprise') {
    return 'enterprise';
  }
  return 'none';
}

export function useSelectFilters() {
  const { data } = useFetchAgentList({});

  const canvasCategory = useMemo(() => {
    return groupListByType(
      data?.canvas ?? [],
      'canvas_category',
      'canvas_category',
    );
  }, [data?.canvas]);

  const agentTypeList: FilterType[] = useMemo(() => {
    const agents = data?.canvas ?? [];
    let none = 0;
    let personal = 0;
    let enterprise = 0;
    agents.forEach((x: IFlow) => {
      const b = bucketAgentType(x.agent_type);
      if (b === 'none') {
        none += 1;
      } else if (b === 'personal') {
        personal += 1;
      } else {
        enterprise += 1;
      }
    });
    return [
      { id: 'none', label: 'None', count: none },
      { id: 'personal', label: 'Individual', count: personal },
      { id: 'enterprise', label: 'Enterprise', count: enterprise },
    ];
  }, [data?.canvas]);

  const filters: FilterCollection[] = [
    buildOwnersFilter(data?.canvas ?? []),
    {
      field: 'canvasCategory',
      list: canvasCategory,
      label: 'Canvas category',
    },
    {
      field: 'agentType',
      list: agentTypeList,
      label: 'Type',
    },
  ];

  return filters;
}
