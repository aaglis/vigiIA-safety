import type { IncidentStatus } from '../../api/incidents'
import type { OperationEntityStatus, OperationZoneType } from '../../api/operations'

export const SEVERITY_META: Record<string, { label: string; dot: string; soft: string; text: string }> = {
  high: { label: 'Alta', dot: '#C1552B', soft: '#F6E4DC', text: '#B14A22' },
  medium: { label: 'Média', dot: '#C98A2B', soft: '#F3E9D6', text: '#946416' },
  low: { label: 'Baixa', dot: '#2F7D57', soft: '#E4EFE9', text: '#1F6B4A' },
}

export const STATUS_CHIP: Record<IncidentStatus, { label: string; bg: string; color: string; dot: string }> = {
  open: { label: 'Aberto', bg: '#F6E4DC', color: '#B14A22', dot: '#C1552B' },
  acknowledged: { label: 'Reconhecido', bg: '#F3E9D6', color: '#946416', dot: '#C98A2B' },
  resolved: { label: 'Resolvido', bg: '#E4EFE9', color: '#1F6B4A', dot: '#2F7D57' },
  dismissed: { label: 'Descartado', bg: '#EEEAE3', color: '#7C756C', dot: '#A9A398' },
}

export const AUDIT_ACTION_LABEL: Record<string, string> = {
  created: 'Incidente criado',
  'incident.created': 'Incidente criado',
  'incident.acknowledged': 'Incidente reconhecido',
  'incident.resolved': 'Incidente resolvido',
  'incident.dismissed': 'Incidente descartado',
}

export const ENTITY_STATUS_BADGE: Record<OperationEntityStatus, { label: string; bg: string; color: string }> = {
  active: { label: 'ATIVO', bg: '#E4EFE9', color: '#1F6B4A' },
  inactive: { label: 'INATIVO', bg: '#F3E9D6', color: '#946416' },
  suspended: { label: 'SUSPENSO', bg: '#F6E4DC', color: '#B14A22' },
}

export const ZONE_TYPE_BADGE: Record<OperationZoneType, { label: string; bg: string; color: string }> = {
  access: { label: 'ACESSO', bg: '#EAF0F5', color: '#2C4C74' },
  restricted: { label: 'RESTRITA', bg: '#F6E4DC', color: '#B14A22' },
  ppe: { label: 'EPI', bg: '#F3E9D6', color: '#946416' },
}

export function severityMeta(severity: string) {
  return SEVERITY_META[severity.toLowerCase()] ?? { label: severity, dot: '#8E887B', soft: '#EEEAE3', text: '#7C756C' }
}

export function auditActionLabel(action: string) {
  return AUDIT_ACTION_LABEL[action] ?? action
}

export function auditActionDot(action: string) {
  if (action.includes('acknowledg')) return '#946416'
  if (action.includes('resolv')) return '#1F6B4A'
  if (action.includes('dismiss')) return '#7C756C'
  return '#C1552B'
}

export function ruleSeverityBadge(severity: string | null | undefined) {
  const s = (severity ?? '').toLowerCase()
  if (s === 'high') return { label: 'ALTA', bg: '#F6E4DC', color: '#B14A22', dot: '#C1552B' }
  if (s === 'medium') return { label: 'MÉDIA', bg: '#F3E9D6', color: '#946416', dot: '#C98A2B' }
  if (s === 'low') return { label: 'BAIXA', bg: '#E4EFE9', color: '#1F6B4A', dot: '#2F7D57' }
  return { label: '—', bg: '#EEEAE3', color: '#7C756C', dot: '#A9A398' }
}

export function labelOperationStatus(status: OperationEntityStatus) {
  const labels: Record<OperationEntityStatus, string> = { active: 'Ativo', inactive: 'Inativo', suspended: 'Suspenso' }
  return labels[status]
}

export function labelZoneType(zoneType: OperationZoneType) {
  const labels: Record<OperationZoneType, string> = { access: 'Acesso', restricted: 'Restrita', ppe: 'EPI' }
  return labels[zoneType]
}
