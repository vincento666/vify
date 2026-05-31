export type EvaluationTabKey = 'experiments' | 'eval-sets' | 'evaluators' | 'runs' | 'compare'

export interface EvaluationTab {
  key: EvaluationTabKey
  label: string
  cnLabel: string
  description: string
  disabled?: boolean
}

export const EVALUATION_TABS: EvaluationTab[] = [
  {
    key: 'experiments',
    label: 'Experiments',
    cnLabel: '实验',
    description: '验证 Agent 目标变更是否可以发布',
  },
  {
    key: 'eval-sets',
    label: 'Eval Sets',
    cnLabel: '评测集',
    description: '维护可复用的回归用例',
  },
  {
    key: 'evaluators',
    label: 'Evaluators',
    cnLabel: '评估器',
    description: '定义可解释的打分规则',
  },
  {
    key: 'runs',
    label: 'Run Records',
    cnLabel: '运行记录',
    description: '查看历史运行与报告',
  },
  {
    key: 'compare',
    label: 'Compare Analysis',
    cnLabel: '对比分析',
    description: '比较两次运行的提升与回退',
    disabled: false,
  },
]

export function getActiveEvaluationTab(value: string | undefined): EvaluationTabKey {
  return EVALUATION_TABS.some((tab) => tab.key === value)
    ? value as EvaluationTabKey
    : 'experiments'
}
