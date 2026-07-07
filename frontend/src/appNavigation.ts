import {
  ApiOutlined,
  BarChartOutlined,
  CommentOutlined,
  CustomerServiceOutlined,
  ThunderboltOutlined,
  FolderOutlined,
  MessageOutlined,
  MonitorOutlined,
  SettingOutlined,
  ShareAltOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'

import type { HostRuntimeConfig } from './host/request'
import { getHostRuntimeConfig } from './host/request'

export interface ComposerNavItem {
  path: string
  name: string
  label: string
  icon: any
  matches?: string[]
  requiredPermission?: string
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
  { path: '/runtime-ops', name: 'HifyRuntimeOps', label: '运行观测', icon: MonitorOutlined, requiredPermission: 'runtime_ops:read' },
  { path: '/runtime-lab/chat', name: 'HifyRuntimeLabChat', label: '路由对话', icon: CommentOutlined },
  { path: '/chat', name: 'HifyChat', label: '对话', icon: MessageOutlined },
]

export function canAccessComposerNavItem(
  item: Pick<ComposerNavItem, 'requiredPermission'>,
  config: HostRuntimeConfig = getHostRuntimeConfig(),
): boolean {
  return canAccessRequiredPermission(item.requiredPermission, config)
}

export function canAccessRequiredPermission(
  requiredPermission: string | undefined,
  config: HostRuntimeConfig = getHostRuntimeConfig(),
): boolean {
  if (!requiredPermission) return true
  if (!Array.isArray(config.permissions)) return true
  return config.permissions.includes(requiredPermission)
}
