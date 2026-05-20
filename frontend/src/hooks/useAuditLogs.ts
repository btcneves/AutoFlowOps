import { useQuery } from '@tanstack/react-query'
import { type AuditLogFilters, getAuditLogs } from '../api/audit_logs'

export function useAuditLogs(filters: AuditLogFilters = {}) {
  return useQuery({
    queryKey: ['audit-logs', filters],
    queryFn: () => getAuditLogs(filters),
  })
}
