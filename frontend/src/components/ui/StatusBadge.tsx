interface StatusBadgeProps {
  status: 'ok' | 'error' | 'loading'
}

const styles: Record<StatusBadgeProps['status'], string> = {
  ok: 'bg-green-100 text-green-800',
  error: 'bg-red-100 text-red-800',
  loading: 'bg-gray-100 text-gray-600',
}

const labels: Record<StatusBadgeProps['status'], string> = {
  ok: 'Online',
  error: 'Error',
  loading: 'Checking…',
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {labels[status]}
    </span>
  )
}
