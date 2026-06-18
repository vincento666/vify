import {
  ApiOutlined,
  BarChartOutlined,
  CommentOutlined,
  CustomerServiceOutlined,
  ThunderboltOutlined,
  FolderOutlined,
  MessageOutlined,
  SettingOutlined,
  ShareAltOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'

export interface ComposerNavItem {
  path: string
  name: string
  label: string
  icon: any
  matches?: string[]
}

export const composerNavItems: ComposerNavItem[] = [
  { path: '/provider', name: 'HifyProvider', label: '模型管理', icon: SettingOutlined },
  { path: '/agent', name: 'HifyAgent', label: 'Agent', icon: UserOutlined },
  { path: '/knowledge', name: 'HifyKnowledge', label: '知识库', icon: FolderOutlined },
  { path: '/workflows', name: 'HifyWorkflows', label: '工作流', icon: ShareAltOutlined, matches: ['/workflows', '/chatflows'] },
  { path: '/evaluation', name: 'HifyEvaluation', label: '评测', icon: BarChartOutlined },
  { path: '/customer-assistant', name: 'HifyCustomerAssistant', label: '客服助手', icon: CustomerServiceOutlined },
  { path: '/ai-assistant', name: 'HifyAiAssistant', label: 'AI 助手', icon: ThunderboltOutlined },
  { path: '/mcp', name: 'HifyMcp', label: 'MCP 工具', icon: ApiOutlined },
  { path: '/runtime-lab/chat', name: 'HifyRuntimeLabChat', label: '路由对话', icon: CommentOutlined },
  { path: '/chat', name: 'HifyChat', label: '对话', icon: MessageOutlined },
]
