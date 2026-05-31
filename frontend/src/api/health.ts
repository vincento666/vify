import { get } from '@/utils/request'

export interface HealthResponse {
  status: 'UP' | 'DOWN'
  components: Record<string, string>
}

export const getHealth = () => get<HealthResponse>('/v1/health')
