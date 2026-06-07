import {
  ChatLineRound,
  ChatDotRound,
  Connection,
  DataAnalysis,
  Folder,
  Setting,
  Share,
  User,
} from '@element-plus/icons-vue'

export interface ComposerNavItem {
  path: string
  label: string
  icon: any
  matches?: string[]
}

export const composerNavItems: ComposerNavItem[] = [
  { path: '/provider', label: '模型管理', icon: Setting },
  { path: '/agent', label: 'Agent', icon: User },
  { path: '/knowledge', label: '知识库', icon: Folder },
  { path: '/workflows', label: '工作流', icon: Share, matches: ['/workflows', '/chatflows'] },
  { path: '/evaluation', label: '评测', icon: DataAnalysis },
  { path: '/mcp', label: 'MCP 工具', icon: Connection },
  { path: '/runtime-lab/chat', label: '路由对话', icon: ChatLineRound },
  { path: '/chat', label: '对话', icon: ChatDotRound },
]
