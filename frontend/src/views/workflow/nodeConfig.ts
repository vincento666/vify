import type { WorkflowCanvasNode, WorkflowCanvasNodeType } from './flowGraph'

export type NodeConfigFieldType = 'text' | 'textarea' | 'number' | 'select' | 'readonly'

export interface NodeConfigField {
  key: string
  label: string
  type: NodeConfigFieldType
  placeholder?: string
  options?: string[]
}

export interface NodeConfigSection {
  title: string
  fields: NodeConfigField[]
}

export interface NodeConfigSchema {
  type: WorkflowCanvasNodeType
  title: string
  sections: NodeConfigSection[]
}

const BASE_SECTION: NodeConfigSection = {
  title: '基础信息',
  fields: [{ key: 'name', label: '节点名称', type: 'text' }],
}

const SCHEMAS: Record<WorkflowCanvasNodeType, NodeConfigSchema> = {
  START: {
    type: 'START',
    title: '开始',
    sections: [
      BASE_SECTION,
      {
        title: '输入变量',
        fields: [{ key: 'outputVariables', label: '输出变量', type: 'readonly' }],
      },
    ],
  },
  LLM: {
    type: 'LLM',
    title: '大模型',
    sections: [
      BASE_SECTION,
      {
        title: '模型',
        fields: [
          { key: 'prompt', label: '模型提示词', type: 'textarea', placeholder: '输入模型提示词，可使用变量引用' },
          { key: 'outputVariable', label: '输出变量', type: 'text', placeholder: 'output' },
        ],
      },
    ],
  },
  CONDITION: {
    type: 'CONDITION',
    title: '条件',
    sections: [
      BASE_SECTION,
      {
        title: '条件判断',
        fields: [
          { key: 'expression', label: '判断表达式', type: 'textarea', placeholder: '{{start.USER_INPUT}} == \"售后\"' },
          { key: 'outputVariable', label: '输出变量', type: 'text', placeholder: 'route' },
        ],
      },
    ],
  },
  KNOWLEDGE: {
    type: 'KNOWLEDGE',
    title: '知识库',
    sections: [
      BASE_SECTION,
      {
        title: '召回配置',
        fields: [
          { key: 'knowledgeBaseId', label: '知识库 ID', type: 'text', placeholder: '1' },
          { key: 'topK', label: '召回数量', type: 'number', placeholder: '5' },
          { key: 'outputVariable', label: '输出变量', type: 'text', placeholder: 'references' },
        ],
      },
    ],
  },
  API_CALL: {
    type: 'API_CALL',
    title: 'API 调用',
    sections: [
      BASE_SECTION,
      {
        title: '请求',
        fields: [
          { key: 'endpoint', label: '请求地址', type: 'text', placeholder: 'https://api.example.com' },
          { key: 'method', label: '请求方法', type: 'select', options: ['GET', 'POST', 'PUT', 'DELETE'] },
          { key: 'outputVariable', label: '输出变量', type: 'text', placeholder: 'response' },
        ],
      },
    ],
  },
  END: {
    type: 'END',
    title: '结束',
    sections: [
      BASE_SECTION,
      {
        title: '输出',
        fields: [{ key: 'outputVariable', label: '返回变量', type: 'text', placeholder: 'output' }],
      },
    ],
  },
}

export function getNodeConfigSchema(type: WorkflowCanvasNodeType): NodeConfigSchema {
  return SCHEMAS[type]
}

export function applyNodeConfigPatch(
  node: WorkflowCanvasNode,
  patch: { name?: string; config?: Record<string, any> },
): WorkflowCanvasNode {
  return {
    ...node,
    name: patch.name ?? node.name,
    config: {
      ...node.config,
      ...(patch.config || {}),
      ui: node.config.ui,
    },
  }
}
