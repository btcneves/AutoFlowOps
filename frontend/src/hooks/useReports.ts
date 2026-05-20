import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { generateReport, getReports } from '../api/reports'
import type { ReportGenerateRequest, ReportSummaryRead } from '../types'

export function useReports() {
  return useQuery<ReportSummaryRead[]>({
    queryKey: ['reports'],
    queryFn: getReports,
    refetchInterval: 30_000,
  })
}

export function useGenerateReport() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (payload: ReportGenerateRequest) => generateReport(payload),
    onSuccess: () => client.invalidateQueries({ queryKey: ['reports'] }),
  })
}
