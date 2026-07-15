import { useEffect, useMemo, useRef, useState } from 'react'
import type { MeResponse } from './api/auth'
import { login, me } from './api/auth'
import { ApiError, isApiError, isSessionError } from './api/client'
import type { OperationCatalog, OperationEntityStatus, OperationZoneType } from './api/operations'
import { getOperationsCatalog } from './api/operations'
import type { AuditLogEntry, Incident, IncidentStatus } from './api/incidents'
import { acknowledgeIncident, dismissIncident, getIncident, getIncidentAuditLog, listIncidents, resolveIncident } from './api/incidents'
import type { EvidenceItem } from './api/evidence'
import { getEvidenceDownloadUrl, listEvidence } from './api/evidence'

type Screen = 'landing' | 'login' | 'dashboard'
type ConnectionMode = 'live' | 'demo' | null

type DemoState = {
  me: MeResponse
  incidents: Incident[]
  auditLogs: Record<string, AuditLogEntry[]>
}

const demoOrganization = { id: 'org-dev', name: 'VigIA Local', slug: 'vigia-local' }
const demoEmail = 'admin@vigia.local'
const demoPassword = 'change-me-dev'

const demoMe: MeResponse = {
  user: {
    id: 'user-dev',
    email: demoEmail,
    full_name: 'VigIA Admin',
  },
  memberships: [
    {
      organization: demoOrganization,
      role: 'owner',
      permissions: ['incidents.read', 'incidents.acknowledge', 'incidents.resolve', 'incidents.dismiss', 'audit.read'],
      active: true,
    },
  ],
  active_organization: demoOrganization,
  active_permissions: ['incidents.read', 'incidents.acknowledge', 'incidents.resolve', 'incidents.dismiss', 'audit.read'],
}

const now = Date.now()
const minutesAgo = (minutes: number) => new Date(now - minutes * 60_000).toISOString()

const demoState: DemoState = {
  me: demoMe,
  incidents: [
    {
      id: 'inc-demo-1',
      organization_id: demoOrganization.id,
      site_id: 'Pátio Sul',
      detection_event_id: 'evt-demo-1',
      camera_id: 'cam-07',
      zone_id: 'zona-armazenagem',
      worker_id: null,
      event_type: 'detection',
      severity: 'high',
      summary: 'Pessoa próxima à área restrita',
      confidence: 0.94,
      metadata: { site_label: 'Pátio Sul', camera_label: 'Câmera 07' },
      status: 'open',
      created_at: minutesAgo(18),
      updated_at: minutesAgo(18),
      acknowledged_at: null,
      resolved_at: null,
      dismissed_at: null,
    },
    {
      id: 'inc-demo-2',
      organization_id: demoOrganization.id,
      site_id: 'Linha 2',
      detection_event_id: 'evt-demo-2',
      camera_id: 'cam-12',
      zone_id: 'linha-pintura',
      worker_id: 'worker-11',
      event_type: 'detection',
      severity: 'medium',
      summary: 'Ausência de EPI em zona controlada',
      confidence: 0.88,
      metadata: { site_label: 'Linha 2', camera_label: 'Câmera 12' },
      status: 'acknowledged',
      created_at: minutesAgo(42),
      updated_at: minutesAgo(34),
      acknowledged_at: minutesAgo(34),
      resolved_at: null,
      dismissed_at: null,
    },
    {
      id: 'inc-demo-3',
      organization_id: demoOrganization.id,
      site_id: 'Doca Norte',
      detection_event_id: 'evt-demo-3',
      camera_id: 'cam-03',
      zone_id: 'acesso-veiculos',
      worker_id: null,
      event_type: 'detection',
      severity: 'low',
      summary: 'Fluxo incomum em passagem de veículos',
      confidence: 0.79,
      metadata: { site_label: 'Doca Norte', camera_label: 'Câmera 03' },
      status: 'resolved',
      created_at: minutesAgo(120),
      updated_at: minutesAgo(92),
      acknowledged_at: minutesAgo(111),
      resolved_at: minutesAgo(92),
      dismissed_at: null,
    },
  ],
  auditLogs: {
    'inc-demo-1': [
      {
        id: 'log-demo-1a',
        organization_id: demoOrganization.id,
        incident_id: 'inc-demo-1',
        action: 'created',
        from_status: null,
        to_status: 'open',
        actor: 'system',
        created_at: minutesAgo(18),
        metadata: { source: 'demo' },
      },
    ],
    'inc-demo-2': [
      {
        id: 'log-demo-2a',
        organization_id: demoOrganization.id,
        incident_id: 'inc-demo-2',
        action: 'created',
        from_status: null,
        to_status: 'open',
        actor: 'system',
        created_at: minutesAgo(42),
        metadata: { source: 'demo' },
      },
      {
        id: 'log-demo-2b',
        organization_id: demoOrganization.id,
        incident_id: 'inc-demo-2',
        action: 'incident.acknowledged',
        from_status: 'open',
        to_status: 'acknowledged',
        actor: 'operator',
        created_at: minutesAgo(34),
        metadata: { source: 'demo' },
      },
    ],
    'inc-demo-3': [
      {
        id: 'log-demo-3a',
        organization_id: demoOrganization.id,
        incident_id: 'inc-demo-3',
        action: 'created',
        from_status: null,
        to_status: 'open',
        actor: 'system',
        created_at: minutesAgo(120),
        metadata: { source: 'demo' },
      },
      {
        id: 'log-demo-3b',
        organization_id: demoOrganization.id,
        incident_id: 'inc-demo-3',
        action: 'incident.acknowledged',
        from_status: 'open',
        to_status: 'acknowledged',
        actor: 'operator',
        created_at: minutesAgo(111),
        metadata: { source: 'demo' },
      },
      {
        id: 'log-demo-3c',
        organization_id: demoOrganization.id,
        incident_id: 'inc-demo-3',
        action: 'incident.resolved',
        from_status: 'acknowledged',
        to_status: 'resolved',
        actor: 'operator',
        created_at: minutesAgo(92),
        metadata: { source: 'demo' },
      },
    ],
  },
}

function makeDemoFrame(title: string, label: string, accent: string) {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
      <defs>
        <linearGradient id="g" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="#0f1419"/>
          <stop offset="100%" stop-color="#1f2933"/>
        </linearGradient>
      </defs>
      <rect width="1280" height="720" fill="url(#g)"/>
      <rect x="84" y="72" width="1112" height="576" rx="34" fill="none" stroke="${accent}" stroke-opacity="0.52" stroke-width="6"/>
      <rect x="104" y="94" width="1068" height="532" rx="26" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.12)"/>
      <g fill="none" stroke="rgba(255,255,255,0.16)" stroke-width="2">
        <path d="M170 190h220" />
        <path d="M170 230h160" />
        <path d="M170 270h300" />
      </g>
      <circle cx="944" cy="310" r="118" fill="none" stroke="${accent}" stroke-opacity="0.45" stroke-width="12"/>
      <circle cx="944" cy="310" r="42" fill="${accent}" fill-opacity="0.8"/>
      <text x="170" y="170" fill="#f5f3ef" font-family="IBM Plex Sans, Arial" font-size="38" font-weight="600">${title}</text>
      <text x="170" y="344" fill="#d7dde4" font-family="IBM Plex Mono, monospace" font-size="24">${label}</text>
      <text x="170" y="402" fill="#8f9aab" font-family="IBM Plex Sans, Arial" font-size="20">Triagem demo · evidência sintética</text>
    </svg>
  `
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

const demoEvidenceByIncident: Record<string, { items: EvidenceItem[]; previewUrls: Record<string, string> }> = {
  'inc-demo-1': {
    items: [
      {
        file_id: 'ev-demo-1-snapshot',
        organization_id: demoOrganization.id,
        incident_id: 'inc-demo-1',
        object_key: 'org/org-dev/incidents/inc-demo-1/evidence/ev-demo-1-snapshot',
        media_type: 'image/svg+xml',
        size: 4821,
        source: 'edge_worker',
        uploaded_by: 'worker-cam-07',
        kind: 'snapshot',
        created_at: minutesAgo(18),
        deleted_at: null,
        metadata: {
          confidence: 0.94,
          model_version: 'real-cv-0.8.2',
          event_type: 'detection',
          frame_timestamp: minutesAgo(18),
          source_type: 'camera',
          site_id: 'Pátio Sul',
          camera_id: 'cam-07',
          zone_id: 'zona-armazenagem',
          sha256: 'a91f9d1e6c0a5c0f1b3a43eac9f2e1ff9c3f1c2a9f3b71d4b0aaf2a8c5b6e1d9',
        },
      },
    ],
    previewUrls: {
      'ev-demo-1-snapshot': makeDemoFrame('Pessoa próxima à área restrita', 'Câmera 07 · Pátio Sul', '#c1552b'),
    },
  },
  'inc-demo-2': {
    items: [
      {
        file_id: 'ev-demo-2-clip',
        organization_id: demoOrganization.id,
        incident_id: 'inc-demo-2',
        object_key: 'org/org-dev/incidents/inc-demo-2/evidence/ev-demo-2-clip',
        media_type: 'video/mp4',
        size: 1083421,
        source: 'edge_worker',
        uploaded_by: 'worker-cam-12',
        kind: 'clip',
        created_at: minutesAgo(42),
        deleted_at: null,
        metadata: {
          confidence: 0.88,
          model_version: 'real-cv-0.8.2',
          event_type: 'detection',
          frame_timestamp: minutesAgo(42),
          source_type: 'camera',
          site_id: 'Linha 2',
          camera_id: 'cam-12',
          zone_id: 'linha-pintura',
          sha256: 'b71e4c3a9f0b2c1d7e3f5a8b9c1d2e3f4a5b6c7d8e9f00112233445566778899',
        },
      },
    ],
    previewUrls: {},
  },
  'inc-demo-3': { items: [], previewUrls: {} },
}

const demoOperationsCatalog: OperationCatalog = {
  organization_id: demoOrganization.id,
  sites: [
    {
      id: 'site-demo-patio-sul',
      organization_id: demoOrganization.id,
      name: 'Pátio Sul',
      address: 'Portaria 2 · área externa',
      status: 'active',
      cameras: [
        { id: 'camera-demo-07', organization_id: demoOrganization.id, site_id: 'site-demo-patio-sul', name: 'Câmera 07', stream_identifier: 'rtsp://demo/camera-07', status: 'active' },
      ],
      zones: [
        { id: 'zone-demo-armazenagem', organization_id: demoOrganization.id, site_id: 'site-demo-patio-sul', camera_id: 'camera-demo-07', zone_type: 'restricted', status: 'active' },
      ],
      safety_rules: [
        { id: 'rule-demo-helmet', organization_id: demoOrganization.id, site_id: 'site-demo-patio-sul', zone_id: 'zone-demo-armazenagem', name: 'Capacete obrigatório', status: 'active', metadata: { severity: 'high', source: 'demo' } },
      ],
      required_ppe: [
        { id: 'ppe-demo-helmet', organization_id: demoOrganization.id, rule_id: 'rule-demo-helmet', site_id: 'site-demo-patio-sul', zone_id: 'zone-demo-armazenagem', item: 'capacete', status: 'active' },
      ],
    },
    {
      id: 'site-demo-linha-2',
      organization_id: demoOrganization.id,
      name: 'Linha 2',
      address: 'Galpão principal · pintura',
      status: 'active',
      cameras: [
        { id: 'camera-demo-12', organization_id: demoOrganization.id, site_id: 'site-demo-linha-2', name: 'Câmera 12', stream_identifier: 'rtsp://demo/camera-12', status: 'active' },
      ],
      zones: [
        { id: 'zone-demo-pintura', organization_id: demoOrganization.id, site_id: 'site-demo-linha-2', camera_id: 'camera-demo-12', zone_type: 'ppe', status: 'active' },
      ],
      safety_rules: [
        { id: 'rule-demo-oculos', organization_id: demoOrganization.id, site_id: 'site-demo-linha-2', zone_id: 'zone-demo-pintura', name: 'Óculos de proteção', status: 'active', metadata: { severity: 'medium', source: 'demo' } },
      ],
      required_ppe: [
        { id: 'ppe-demo-oculos', organization_id: demoOrganization.id, rule_id: 'rule-demo-oculos', site_id: 'site-demo-linha-2', zone_id: 'zone-demo-pintura', item: 'óculos', status: 'active' },
      ],
    },
    {
      id: 'site-demo-doca-norte',
      organization_id: demoOrganization.id,
      name: 'Doca Norte',
      address: 'Recebimento de cargas',
      status: 'inactive',
      cameras: [
        { id: 'camera-demo-03', organization_id: demoOrganization.id, site_id: 'site-demo-doca-norte', name: 'Câmera 03', stream_identifier: 'rtsp://demo/camera-03', status: 'inactive' },
      ],
      zones: [
        { id: 'zone-demo-veiculos', organization_id: demoOrganization.id, site_id: 'site-demo-doca-norte', camera_id: 'camera-demo-03', zone_type: 'access', status: 'inactive' },
      ],
      safety_rules: [
        { id: 'rule-demo-faixa', organization_id: demoOrganization.id, site_id: 'site-demo-doca-norte', zone_id: 'zone-demo-veiculos', name: 'Área isolada para veículos', status: 'inactive', metadata: { source: 'demo' } },
      ],
      required_ppe: [
        { id: 'ppe-demo-faixa', organization_id: demoOrganization.id, rule_id: 'rule-demo-faixa', site_id: 'site-demo-doca-norte', zone_id: 'zone-demo-veiculos', item: 'faixa refletiva', status: 'inactive' },
      ],
    },
  ],
  cameras: [
    { id: 'camera-demo-07', organization_id: demoOrganization.id, site_id: 'site-demo-patio-sul', name: 'Câmera 07', stream_identifier: 'rtsp://demo/camera-07', status: 'active' },
    { id: 'camera-demo-12', organization_id: demoOrganization.id, site_id: 'site-demo-linha-2', name: 'Câmera 12', stream_identifier: 'rtsp://demo/camera-12', status: 'active' },
    { id: 'camera-demo-03', organization_id: demoOrganization.id, site_id: 'site-demo-doca-norte', name: 'Câmera 03', stream_identifier: 'rtsp://demo/camera-03', status: 'inactive' },
  ],
  zones: [
    { id: 'zone-demo-armazenagem', organization_id: demoOrganization.id, site_id: 'site-demo-patio-sul', camera_id: 'camera-demo-07', zone_type: 'restricted', status: 'active' },
    { id: 'zone-demo-pintura', organization_id: demoOrganization.id, site_id: 'site-demo-linha-2', camera_id: 'camera-demo-12', zone_type: 'ppe', status: 'active' },
    { id: 'zone-demo-veiculos', organization_id: demoOrganization.id, site_id: 'site-demo-doca-norte', camera_id: 'camera-demo-03', zone_type: 'access', status: 'inactive' },
  ],
  safety_rules: [
    { id: 'rule-demo-helmet', organization_id: demoOrganization.id, site_id: 'site-demo-patio-sul', zone_id: 'zone-demo-armazenagem', name: 'Capacete obrigatório', status: 'active', metadata: { severity: 'high', source: 'demo' } },
    { id: 'rule-demo-oculos', organization_id: demoOrganization.id, site_id: 'site-demo-linha-2', zone_id: 'zone-demo-pintura', name: 'Óculos de proteção', status: 'active', metadata: { severity: 'medium', source: 'demo' } },
    { id: 'rule-demo-faixa', organization_id: demoOrganization.id, site_id: 'site-demo-doca-norte', zone_id: 'zone-demo-veiculos', name: 'Área isolada para veículos', status: 'inactive', metadata: { source: 'demo' } },
  ],
  required_ppe: [
    { id: 'ppe-demo-helmet', organization_id: demoOrganization.id, rule_id: 'rule-demo-helmet', site_id: 'site-demo-patio-sul', zone_id: 'zone-demo-armazenagem', item: 'capacete', status: 'active' },
    { id: 'ppe-demo-oculos', organization_id: demoOrganization.id, rule_id: 'rule-demo-oculos', site_id: 'site-demo-linha-2', zone_id: 'zone-demo-pintura', item: 'óculos', status: 'active' },
    { id: 'ppe-demo-faixa', organization_id: demoOrganization.id, rule_id: 'rule-demo-faixa', site_id: 'site-demo-doca-norte', zone_id: 'zone-demo-veiculos', item: 'faixa refletiva', status: 'inactive' },
  ],
}

const navItems = [
  { label: 'Produto', id: 'produto' },
  { label: 'Como funciona', id: 'como-funciona' },
  { label: 'Segurança', id: 'seguranca' },
] as const

const flowSteps = [
  { title: 'Detecção na borda', text: 'Edge workers leem câmeras e enviam apenas eventos de risco — sem vídeo contínuo.' },
  { title: 'Triagem no dashboard', text: 'O evento vira incidente priorizado e chega à equipe certa para resposta rápida.' },
  { title: 'Registro auditável', text: 'Ação, evidência e histórico ficam registrados para auditoria e conformidade.' },
] as const

const securityPoints = [
  { title: 'Sem reconhecimento facial', text: 'Nenhuma identificação biométrica no MVP.' },
  { title: 'Sem vídeo contínuo', text: 'Apenas eventos e evidências curtas quando necessário.' },
  { title: 'Evidências privadas', text: 'Isoladas por organização, com URLs assinadas e auditoria de acesso.' },
  { title: 'Auditoria completa', text: 'Trilha de ações sensíveis e retenção configurável por organização.' },
] as const

const features = [
  {
    eyebrow: 'Monitoramento',
    title: 'Enxergue o risco antes do acidente',
    description: 'Leitura contínua do ambiente, com foco em prevenção, triagem e resposta rápida.',
  },
  {
    eyebrow: 'Operação',
    title: 'Fluxo simples para equipes reais',
    description: 'Alertas diretos, contexto claro e acesso restrito para quem precisa agir.',
  },
  {
    eyebrow: 'Auditoria',
    title: 'Rastro limpo para conformidade',
    description: 'Eventos organizados, decisões rastreáveis e histórico pronto para revisão.',
  },
] as const

type IncidentPeriod = 'all' | '24h' | '7d' | '30d' | 'custom'

type IncidentFilters = {
  status: IncidentStatus | 'all'
  severity: string
  siteId: string
  cameraId: string
  zoneId: string
  period: IncidentPeriod
  createdFrom: string
  createdTo: string
}

const defaultIncidentFilters: IncidentFilters = {
  status: 'all',
  severity: 'all',
  siteId: 'all',
  cameraId: 'all',
  zoneId: 'all',
  period: 'all',
  createdFrom: '',
  createdTo: '',
}

function getPresetRange(period: Exclude<IncidentPeriod, 'all' | 'custom'>) {
  const end = new Date()
  const start = new Date(end)
  if (period === '24h') {
    start.setHours(start.getHours() - 24)
  } else if (period === '7d') {
    start.setDate(start.getDate() - 7)
  } else {
    start.setDate(start.getDate() - 30)
  }
  return { createdFrom: start.toISOString(), createdTo: end.toISOString() }
}

function normalizeCreatedFromValue(value: string) {
  if (!value) return ''
  if (value.includes('T')) {
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? '' : date.toISOString()
  }
  const date = new Date(`${value}T00:00:00`)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString()
}

function normalizeCreatedToValue(value: string) {
  if (!value) return ''
  if (value.includes('T')) {
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? '' : date.toISOString()
  }
  const date = new Date(`${value}T23:59:59.999`)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString()
}

function incidentMatchesFilters(incident: Incident, filters: IncidentFilters) {
  if (filters.status !== 'all' && incident.status !== filters.status) return false
  if (filters.severity !== 'all' && incident.severity.toLowerCase() !== filters.severity.toLowerCase()) return false
  if (filters.siteId !== 'all' && (incident.site_id ?? '') !== filters.siteId) return false
  if (filters.cameraId !== 'all' && incident.camera_id !== filters.cameraId) return false
  if (filters.zoneId !== 'all' && incident.zone_id !== filters.zoneId) return false

  const createdAt = new Date(incident.created_at).getTime()
  if (filters.createdFrom && createdAt < new Date(filters.createdFrom).getTime()) return false
  if (filters.createdTo && createdAt > new Date(filters.createdTo).getTime()) return false

  return true
}

function normalizeIncidentFilters(filters: IncidentFilters): IncidentFilters {
  const next = { ...filters }
  if (next.period === 'all') {
    next.createdFrom = ''
    next.createdTo = ''
  } else if (next.period === '24h' || next.period === '7d' || next.period === '30d') {
    const range = getPresetRange(next.period)
    next.createdFrom = range.createdFrom
    next.createdTo = range.createdTo
  } else if (next.period === 'custom') {
    next.createdFrom = next.createdFrom ? normalizeCreatedFromValue(next.createdFrom) : ''
    next.createdTo = next.createdTo ? normalizeCreatedToValue(next.createdTo) : ''
  }
  return next
}

function readIncidentFiltersFromUrl(): IncidentFilters {
  if (typeof window === 'undefined') return { ...defaultIncidentFilters }
  const params = new URLSearchParams(window.location.search)
  const periodParam = params.get('period')
  const period = periodParam === '24h' || periodParam === '7d' || periodParam === '30d' || periodParam === 'custom' ? periodParam : 'all'
  const status = params.get('status')
  const severity = params.get('severity') ?? 'all'
  const siteId = params.get('site_id') ?? 'all'
  const cameraId = params.get('camera_id') ?? 'all'
  const zoneId = params.get('zone_id') ?? 'all'
  const createdFrom = params.get('created_from') ?? ''
  const createdTo = params.get('created_to') ?? ''

  const next: IncidentFilters = {
    status: status === 'open' || status === 'acknowledged' || status === 'resolved' || status === 'dismissed' ? status : 'all',
    severity: severity || 'all',
    siteId: siteId || 'all',
    cameraId: cameraId || 'all',
    zoneId: zoneId || 'all',
    period,
    createdFrom,
    createdTo,
  }

  if (next.period === 'all' && (createdFrom || createdTo)) {
    next.period = 'custom'
  }

  return normalizeIncidentFilters(next)
}

function writeIncidentFiltersToUrl(filters: IncidentFilters) {
  if (typeof window === 'undefined') return
  const params = new URLSearchParams()
  if (filters.status !== 'all') params.set('status', filters.status)
  if (filters.severity !== 'all') params.set('severity', filters.severity)
  if (filters.siteId !== 'all') params.set('site_id', filters.siteId)
  if (filters.cameraId !== 'all') params.set('camera_id', filters.cameraId)
  if (filters.zoneId !== 'all') params.set('zone_id', filters.zoneId)
  if (filters.period !== 'all') params.set('period', filters.period)
  if (filters.createdFrom) params.set('created_from', filters.createdFrom)
  if (filters.createdTo) params.set('created_to', filters.createdTo)

  const search = params.toString()
  const nextUrl = `${window.location.pathname}${search ? `?${search}` : ''}${window.location.hash}`
  window.history.replaceState({}, '', nextUrl)
}

function formatDateInput(value: string) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString().slice(0, 10)
}

function incidentFiltersToParams(filters: IncidentFilters) {
  const next = normalizeIncidentFilters(filters)
  return {
    status: next.status === 'all' ? undefined : next.status,
    severity: next.severity === 'all' ? undefined : next.severity,
    site_id: next.siteId === 'all' ? undefined : next.siteId,
    camera_id: next.cameraId === 'all' ? undefined : next.cameraId,
    zone_id: next.zoneId === 'all' ? undefined : next.zoneId,
    created_from: next.createdFrom || undefined,
    created_to: next.createdTo || undefined,
  }
}

function MonogramMark({ className = '', variant = 'default' }: { className?: string; variant?: 'default' | 'reverse' }) {
  const outline = variant === 'reverse' ? '#F5F3EF' : '#201B18'
  const inner = variant === 'reverse' ? '#E07A4E' : '#C1552B'
  return (
    <svg viewBox="0 0 120 120" className={className} aria-hidden="true">
      <rect x="10" y="10" width="100" height="100" rx="28" fill="none" stroke={outline} strokeWidth="9" />
      <rect x="42" y="42" width="36" height="36" rx="7" fill={inner} />
    </svg>
  )
}

function Logo({ markClassName = 'h-9 w-9', size = 'md', variant = 'default' }: { markClassName?: string; size?: 'sm' | 'md' | 'lg'; variant?: 'default' | 'reverse' }) {
  const vigiaSize = size === 'lg' ? 'text-2xl' : size === 'sm' ? 'text-[15px]' : 'text-lg'
  const safetySize = size === 'lg' ? 'text-[11px]' : 'text-[8px]'
  const vigiaColor = variant === 'reverse' ? 'text-[var(--paper)]' : 'text-[var(--ink)]'
  return (
    <span className="flex items-center gap-2.5">
      <MonogramMark className={markClassName} variant={variant} />
      <span className="flex flex-col leading-none">
        <span className={`font-semibold tracking-[0.03em] ${vigiaSize} ${vigiaColor}`}>VIGIA</span>
        <span className={`mt-1 font-mono-ui uppercase tracking-[0.34em] text-[var(--label)] ${safetySize}`}>SAFETY</span>
      </span>
    </span>
  )
}

function SectionHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div className="max-w-2xl">
      <p className="font-mono-ui text-[11px] uppercase tracking-[0.32em] text-[var(--accent)]">{eyebrow}</p>
      <h2 className="mt-3 font-display text-3xl leading-tight text-[var(--ink)] md:text-4xl">{title}</h2>
      <p className="mt-4 max-w-xl text-sm leading-7 text-[var(--muted)] md:text-base">{description}</p>
    </div>
  )
}

function StatusPill({ status }: { status: IncidentStatus }) {
  const styles: Record<IncidentStatus, string> = {
    open: 'bg-[rgba(201,138,43,0.16)] text-[#7a5314] border-[rgba(201,138,43,0.25)]',
    acknowledged: 'bg-[rgba(47,125,87,0.14)] text-[#236444] border-[rgba(47,125,87,0.22)]',
    resolved: 'bg-[rgba(32,27,24,0.9)] text-[var(--paper)] border-[rgba(32,27,24,0.8)]',
    dismissed: 'bg-[rgba(193,85,43,0.16)] text-[#9e4120] border-[rgba(193,85,43,0.28)]',
  }

  const labels: Record<IncidentStatus, string> = {
    open: 'Aberto',
    acknowledged: 'Reconhecido',
    resolved: 'Resolvido',
    dismissed: 'Descartado',
  }

  return <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-medium ${styles[status]}`}>{labels[status]}</span>
}

function SeverityPill({ severity }: { severity: string }) {
  const normalized = severity.toLowerCase()
  const tone = normalized === 'high' ? 'bg-[rgba(193,85,43,0.16)] text-[#8f3c1c]' : normalized === 'medium' ? 'bg-[rgba(201,138,43,0.18)] text-[#7a5314]' : 'bg-[rgba(47,125,87,0.14)] text-[#236444]'
  return <span className={`inline-flex rounded-full border border-black/5 px-3 py-1 text-xs font-medium capitalize ${tone}`}>{severity}</span>
}

function formatTimestamp(value: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

function formatBytes(size: number) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function shortHash(value: string | undefined) {
  if (!value) return '—'
  return value.length > 14 ? `${value.slice(0, 6)}…${value.slice(-6)}` : value
}

function labelOperationStatus(status: OperationEntityStatus) {
  const labels: Record<OperationEntityStatus, string> = {
    active: 'Ativo',
    inactive: 'Inativo',
    suspended: 'Suspenso',
  }

  return labels[status]
}

function labelZoneType(zoneType: OperationZoneType) {
  const labels: Record<OperationZoneType, string> = {
    access: 'Acesso',
    restricted: 'Restrita',
    ppe: 'EPI',
  }

  return labels[zoneType]
}

function OperationStatusPill({ status }: { status: OperationEntityStatus }) {
  const styles: Record<OperationEntityStatus, string> = {
    active: 'bg-[rgba(47,125,87,0.14)] text-[#236444] border-[rgba(47,125,87,0.22)]',
    inactive: 'bg-[rgba(201,138,43,0.16)] text-[#7a5314] border-[rgba(201,138,43,0.25)]',
    suspended: 'bg-[rgba(193,85,43,0.16)] text-[#9e4120] border-[rgba(193,85,43,0.28)]',
  }

  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.18em] ${styles[status]}`}>{labelOperationStatus(status)}</span>
}

function ZoneTypePill({ zoneType }: { zoneType: OperationZoneType }) {
  const styles: Record<OperationZoneType, string> = {
    access: 'bg-[rgba(32,27,24,0.9)] text-[var(--paper)] border-[rgba(32,27,24,0.8)]',
    restricted: 'bg-[rgba(193,85,43,0.16)] text-[#9e4120] border-[rgba(193,85,43,0.28)]',
    ppe: 'bg-[rgba(201,138,43,0.16)] text-[#7a5314] border-[rgba(201,138,43,0.25)]',
  }

  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.18em] ${styles[zoneType]}`}>{labelZoneType(zoneType)}</span>
}

function getEvidenceLabel(evidence: EvidenceItem) {
  return evidence.kind === 'clip' ? 'Vídeo' : evidence.kind === 'metadata' ? 'Metadado' : 'Snapshot'
}

function readMetadataValue(metadata: Record<string, unknown> | undefined, key: string) {
  if (!metadata) return null
  const value = metadata[key]
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return null
}

function selectOrganization(meResponse: MeResponse) {
  return meResponse.active_organization ?? meResponse.memberships.find((membership) => membership.active)?.organization ?? meResponse.memberships[0]?.organization ?? null
}

function normalizeApiError(error: unknown) {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return 'Não foi possível conectar à API.'
}

function EvidenceExplorer({
  incident,
  organizationName,
  evidenceItems,
  selectedEvidence,
  evidenceLoading,
  evidenceError,
  evidenceDownloadUrl,
  evidenceDownloadLoading,
  evidenceDownloadError,
  onSelectEvidence,
  onOpenEvidence,
  onRetry,
}: {
  incident: Incident | null
  organizationName: string | null
  evidenceItems: EvidenceItem[]
  selectedEvidence: EvidenceItem | null
  evidenceLoading: boolean
  evidenceError: string | null
  evidenceDownloadUrl: string | null
  evidenceDownloadLoading: boolean
  evidenceDownloadError: string | null
  onSelectEvidence: (fileId: string) => void
  onOpenEvidence: () => void
  onRetry: () => void
}) {
  const selectedMetadata = selectedEvidence?.metadata ?? {}
  const contentType = selectedEvidence?.media_type ?? readMetadataValue(selectedMetadata, 'content_type') ?? '—'
  const sourceType = readMetadataValue(selectedMetadata, 'source_type') ?? selectedEvidence?.source ?? '—'
  const confidenceValue = selectedMetadata.confidence
  const confidence = typeof confidenceValue === 'number'
    ? `${Math.round(confidenceValue * 100)}%`
    : typeof confidenceValue === 'string' && confidenceValue.trim().length > 0
      ? confidenceValue
      : incident?.confidence != null
        ? `${Math.round(incident.confidence * 100)}%`
        : '—'
  const modelVersion = readMetadataValue(selectedMetadata, 'model_version') ?? '—'
  const frameTimestamp = readMetadataValue(selectedMetadata, 'frame_timestamp') ?? formatTimestamp(selectedEvidence?.created_at ?? null)
  const sha256 = readMetadataValue(selectedMetadata, 'sha256') ?? '—'
  const camera = readMetadataValue(selectedMetadata, 'camera_id') ?? incident?.camera_id ?? '—'
  const zone = readMetadataValue(selectedMetadata, 'zone_id') ?? incident?.zone_id ?? '—'
  const site = readMetadataValue(selectedMetadata, 'site_id') ?? incident?.site_id ?? '—'
  const eventType = readMetadataValue(selectedMetadata, 'event_type') ?? incident?.event_type ?? '—'
  const selectedKindLabel = selectedEvidence ? getEvidenceLabel(selectedEvidence) : 'Evidência'
  const hasImagePreview = Boolean(evidenceDownloadUrl && selectedEvidence?.media_type.startsWith('image/'))

  return (
    <section className="rounded-[34px] border border-[color:var(--line)] bg-[rgba(18,22,28,0.96)] p-6 text-[var(--paper)] shadow-[0_26px_80px_rgba(32,27,24,0.18)]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono-ui text-[11px] uppercase tracking-[0.3em] text-[rgba(205,218,230,0.72)]">Evidência visual</p>
          <h3 className="mt-3 font-display text-3xl leading-tight">Visor de câmera</h3>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-[rgba(223,231,239,0.76)]">
            Revisão rápida sob pressão: imagem, metadados, confiança do modelo e trilha de captura no mesmo campo de visão.
          </p>
        </div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-[rgba(223,231,239,0.72)]">
          {organizationName ?? 'Organização ativa'}
        </div>
      </div>

      {evidenceError ? (
        <div className="mt-5 rounded-[24px] border border-[rgba(193,85,43,0.25)] bg-[rgba(193,85,43,0.12)] px-4 py-3 text-sm text-[#ffccb8]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p>{evidenceError}</p>
            <button type="button" onClick={onRetry} className="font-medium text-white underline decoration-white/40 underline-offset-4 transition hover:opacity-80">
              Tentar de novo
            </button>
          </div>
        </div>
      ) : null}

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.06fr_0.94fr]">
        <div className="rounded-[30px] border border-[rgba(154,179,199,0.22)] bg-[linear-gradient(180deg,rgba(11,15,20,0.98),rgba(20,28,36,0.98))] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
          <div className="flex items-center justify-between gap-3 border-b border-white/8 pb-3 text-[11px] uppercase tracking-[0.24em] text-[rgba(205,218,230,0.6)]">
            <span>Frame de triagem</span>
            <span>{selectedKindLabel}</span>
          </div>

          <div className="mt-4 overflow-hidden rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.03)]">
            {evidenceLoading ? (
              <div className="grid min-h-[320px] place-items-center px-6 py-10 text-center text-sm text-[rgba(223,231,239,0.72)]">Carregando evidências…</div>
            ) : evidenceItems.length === 0 ? (
              <div className="grid min-h-[320px] place-items-center px-6 py-10 text-center">
                <div className="max-w-md space-y-3">
                  <p className="font-display text-2xl text-[var(--paper)]">Sem evidência visual registrada para este incidente</p>
                  <p className="text-sm leading-7 text-[rgba(223,231,239,0.72)]">A triagem segue com contexto do incidente, timestamps e auditoria, mas não há snapshot ou clipe anexado.</p>
                </div>
              </div>
            ) : selectedEvidence ? (
              <div className="space-y-4 p-4">
                {evidenceDownloadError ? (
                  <div className="rounded-[20px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.1)] px-4 py-3 text-sm text-[#ffccb8]">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p>{evidenceDownloadError}</p>
                      <button type="button" onClick={onOpenEvidence} className="font-medium text-white underline decoration-white/40 underline-offset-4 transition hover:opacity-80">
                        Tentar abrir novamente
                      </button>
                    </div>
                  </div>
                ) : null}

                {hasImagePreview ? (
                  <div className="space-y-3">
                    <img src={evidenceDownloadUrl ?? ''} alt={selectedEvidence.object_key} className="h-auto w-full rounded-[20px] border border-white/10 bg-black object-cover shadow-[0_16px_40px_rgba(0,0,0,0.35)]" />
                    {evidenceDownloadUrl ? (
                      <div className="flex justify-end">
                        <a href={evidenceDownloadUrl} target="_blank" rel="noreferrer" className="inline-flex rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium uppercase tracking-[0.18em] text-[rgba(223,231,239,0.86)] transition hover:bg-white/10">
                          Abrir em nova aba
                        </a>
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <div className="grid min-h-[240px] place-items-center rounded-[20px] border border-dashed border-[rgba(154,179,199,0.28)] bg-[rgba(255,255,255,0.03)] px-6 py-8 text-center">
                    <div className="max-w-md space-y-3">
                      <p className="font-display text-2xl text-[var(--paper)]">{evidenceDownloadUrl ? 'Evidência aberta com segurança' : 'Abrir evidência segura'}</p>
                      <p className="text-sm leading-7 text-[rgba(223,231,239,0.72)]">{evidenceDownloadUrl ? 'O arquivo foi solicitado via API e pode ser aberto em nova aba.' : 'Clique para solicitar a URL assinada apenas quando precisar ver o arquivo.'}</p>
                      {evidenceDownloadUrl ? (
                        <a href={evidenceDownloadUrl} target="_blank" rel="noreferrer" className="inline-flex rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-medium text-[var(--paper)] shadow-[0_16px_40px_rgba(193,85,43,0.28)] transition hover:-translate-y-0.5">
                          Abrir em nova aba
                        </a>
                      ) : (
                        <button type="button" onClick={onOpenEvidence} disabled={evidenceDownloadLoading} className="inline-flex rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-medium text-[var(--paper)] shadow-[0_16px_40px_rgba(193,85,43,0.28)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60">
                          {evidenceDownloadLoading ? 'Abrindo…' : 'Abrir evidência segura'}
                        </button>
                      )}
                    </div>
                  </div>
                )}

                <div className="grid gap-3 sm:grid-cols-2">
                  {evidenceItems.map((item) => {
                    const active = item.file_id === selectedEvidence.file_id
                    return (
                      <button
                        key={item.file_id}
                        type="button"
                        onClick={() => onSelectEvidence(item.file_id)}
                        className={`rounded-[18px] border px-4 py-3 text-left transition hover:-translate-y-0.5 ${active ? 'border-[rgba(193,85,43,0.3)] bg-[rgba(193,85,43,0.08)]' : 'border-white/8 bg-white/5'}`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-display text-lg text-[var(--paper)]">{getEvidenceLabel(item)}</p>
                          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] uppercase tracking-[0.2em] text-[rgba(223,231,239,0.72)]">{item.kind}</span>
                        </div>
                        <p className="mt-2 text-xs leading-5 text-[rgba(223,231,239,0.68)]">{item.media_type} · {formatBytes(item.size)} · {formatTimestamp(item.created_at)}</p>
                      </button>
                    )
                  })}
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-[30px] border border-white/10 bg-white/5 p-4">
            <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[rgba(223,231,239,0.62)]">Contexto técnico</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {[
                ['Confiança', confidence],
                ['Modelo', modelVersion],
                ['Tipo de evento', eventType],
                ['Câmera', camera],
                ['Zona', zone],
                ['Site', site],
                ['Captura', frameTimestamp],
                ['Fonte', sourceType],
              ].map(([label, value]) => (
                <div key={label} className="rounded-[20px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-3">
                  <p className="text-[10px] uppercase tracking-[0.24em] text-[rgba(223,231,239,0.58)]">{label}</p>
                  <p className="mt-2 text-sm text-[var(--paper)]">{String(value ?? '—')}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[30px] border border-white/10 bg-white/5 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[rgba(223,231,239,0.62)]">Metadados de captura</p>
                <h4 className="mt-3 font-display text-2xl text-[var(--paper)]">{selectedEvidence ? selectedKindLabel : 'Nenhum arquivo selecionado'}</h4>
              </div>
              <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-[rgba(223,231,239,0.72)]">SHA256 {shortHash(sha256)}</div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {[
                ['Content-Type', contentType],
                ['Uploaded by', selectedEvidence?.uploaded_by ?? '—'],
                ['Object key', selectedEvidence?.object_key ?? '—'],
                ['Criado em', formatTimestamp(selectedEvidence?.created_at ?? null)],
              ].map(([label, value]) => (
                <div key={label} className="rounded-[20px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-3 text-sm text-[var(--paper)]">
                  <p className="text-[10px] uppercase tracking-[0.24em] text-[rgba(223,231,239,0.58)]">{label}</p>
                  <p className="mt-2 break-words leading-6">{String(value ?? '—')}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default function App() {
  const [screen, setScreen] = useState<Screen>('landing')
  const [mode, setMode] = useState<ConnectionMode>(null)
  const [booting, setBooting] = useState(true)
  const [banner, setBanner] = useState<string | null>(null)
  const [loginEmail, setLoginEmail] = useState(demoEmail)
  const [loginPassword, setLoginPassword] = useState(demoPassword)
  const [loginLoading, setLoginLoading] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [meData, setMeData] = useState<MeResponse | null>(null)
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null)
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([])
  const [dashboardLoading, setDashboardLoading] = useState(false)
  const [dashboardError, setDashboardError] = useState<string | null>(null)
  const [operationsCatalog, setOperationsCatalog] = useState<OperationCatalog | null>(null)
  const [operationsLoading, setOperationsLoading] = useState(false)
  const [operationsError, setOperationsError] = useState<string | null>(null)
  const [incidentFilters, setIncidentFilters] = useState<IncidentFilters>(() => readIncidentFiltersFromUrl())
  const [actionBusy, setActionBusy] = useState<string | null>(null)
  const [evidenceItems, setEvidenceItems] = useState<EvidenceItem[]>([])
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null)
  const [evidenceLoading, setEvidenceLoading] = useState(false)
  const [evidenceError, setEvidenceError] = useState<string | null>(null)
  const [evidenceDownloadUrl, setEvidenceDownloadUrl] = useState<string | null>(null)
  const [evidenceDownloadLoading, setEvidenceDownloadLoading] = useState(false)
  const [evidenceDownloadError, setEvidenceDownloadError] = useState<string | null>(null)
  const incidentRequestIdRef = useRef(0)

  const activeOrganization = useMemo(() => (meData ? selectOrganization(meData) : null), [meData])
  const selectedIncident = useMemo(() => incidents.find((incident) => incident.id === selectedIncidentId) ?? null, [incidents, selectedIncidentId])
  const selectedEvidence = useMemo(
    () => evidenceItems.find((evidence) => evidence.file_id === selectedEvidenceId) ?? evidenceItems[0] ?? null,
    [evidenceItems, selectedEvidenceId],
  )
  const operationSites = operationsCatalog?.sites ?? []
  const operationCameras = operationsCatalog?.cameras ?? []
  const operationZones = operationsCatalog?.zones ?? []
  const operationRules = operationsCatalog?.safety_rules ?? []
  const operationPpe = operationsCatalog?.required_ppe ?? []
  const filteredSiteOptions = operationSites
  const filteredCameraOptions = incidentFilters.siteId === 'all' ? operationCameras : operationCameras.filter((camera) => camera.site_id === incidentFilters.siteId)
  const filteredZoneOptions = incidentFilters.siteId === 'all' ? operationZones : operationZones.filter((zone) => zone.site_id === incidentFilters.siteId)
  const hasActiveIncidentFilters = incidentFilters.status !== 'all'
    || incidentFilters.severity !== 'all'
    || incidentFilters.siteId !== 'all'
    || incidentFilters.cameraId !== 'all'
    || incidentFilters.zoneId !== 'all'
    || incidentFilters.period !== 'all'
  const incidentSummary = useMemo(
    () => ({
      total: incidents.length,
      open: incidents.filter((incident) => incident.status === 'open').length,
      acknowledged: incidents.filter((incident) => incident.status === 'acknowledged').length,
      resolved: incidents.filter((incident) => incident.status === 'resolved').length,
    }),
    [incidents],
  )

  const scrollToSection = (id: string) => {
    if (screen === 'login' || screen === 'dashboard') setScreen('landing')
    window.setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
  }

  const goLanding = () => {
    setScreen('landing')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const clearIncidentDetailState = () => {
    setAuditLog([])
    setEvidenceItems([])
    setSelectedEvidenceId(null)
    setEvidenceLoading(false)
    setEvidenceError(null)
    setEvidenceDownloadUrl(null)
    setEvidenceDownloadLoading(false)
    setEvidenceDownloadError(null)
  }

  const refreshIncidentList = async (meResponse: MeResponse, nextFilters: IncidentFilters, preferredIncidentId?: string | null) => {
    const organization = selectOrganization(meResponse)
    if (!organization) {
      activateDemo('Nenhuma organização ativa encontrada. Exibindo demonstração local.')
      return
    }

    const normalizedFilters = normalizeIncidentFilters(nextFilters)
    writeIncidentFiltersToUrl(normalizedFilters)

    const currentRequestId = ++incidentRequestIdRef.current
    const previousSelectedId = selectedIncidentId
    const previousSelectedIncident = previousSelectedId ? incidents.find((incident) => incident.id === previousSelectedId) ?? null : null
    const shouldResetSelection = previousSelectedIncident ? !incidentMatchesFilters(previousSelectedIncident, normalizedFilters) : false

    setDashboardLoading(true)
    setDashboardError(null)

    try {
      if (mode === 'demo') {
        const demoIncidents = demoState.incidents.filter((incident) => incidentMatchesFilters(incident, normalizedFilters))
        const nextSelectedId = previousSelectedId && demoIncidents.some((incident) => incident.id === previousSelectedId)
          ? previousSelectedId
          : shouldResetSelection
            ? null
            : preferredIncidentId && demoIncidents.some((incident) => incident.id === preferredIncidentId)
              ? preferredIncidentId
              : previousSelectedId
                ? null
                : demoIncidents[0]?.id ?? null

        setIncidents(demoIncidents)
        setMode('demo')
        setMeData(meResponse)
        setSelectedIncidentId(nextSelectedId)

        if (nextSelectedId) {
          await loadIncidentContext(organization.id, nextSelectedId)
        } else {
          setAuditLog([])
          clearIncidentDetailState()
        }

        return
      }

      const response = await listIncidents(organization.id, {
        limit: 50,
        offset: 0,
        ...incidentFiltersToParams(normalizedFilters),
      })

      if (currentRequestId !== incidentRequestIdRef.current) return

      const items = response.items ?? []
      const nextSelectedId = previousSelectedId && items.some((incident) => incident.id === previousSelectedId)
        ? previousSelectedId
        : shouldResetSelection
          ? null
          : preferredIncidentId && items.some((incident) => incident.id === preferredIncidentId)
            ? preferredIncidentId
            : previousSelectedId
              ? null
              : items[0]?.id ?? null

      setMode('live')
      setMeData(meResponse)
      setIncidents(items)
      setSelectedIncidentId(nextSelectedId)
      setBanner(null)

      if (nextSelectedId) {
        const [incidentDetail, audit] = await Promise.all([
          getIncident(organization.id, nextSelectedId),
          getIncidentAuditLog(organization.id, nextSelectedId, { limit: 50, offset: 0 }),
        ])
        if (currentRequestId !== incidentRequestIdRef.current) return
        setIncidents((current) => current.map((incident) => (incident.id === incidentDetail.id ? incidentDetail : incident)))
        setSelectedIncidentId(incidentDetail.id)
        setAuditLog(audit.items ?? [])
        await loadEvidenceContext(organization.id, incidentDetail.id, currentRequestId)
      } else {
        setAuditLog([])
        clearIncidentDetailState()
      }
    } catch (error) {
      if (isSessionError(error)) {
        expireSession()
        return
      }
      if (mode === 'demo') {
        setDashboardError('A API falhou durante a atualização. Mantendo a demonstração local.')
        return
      }
      activateDemo(`Modo demonstração local ativado: ${normalizeApiError(error)}`)
    } finally {
      if (currentRequestId === incidentRequestIdRef.current) {
        setDashboardLoading(false)
      }
      setBooting(false)
    }
  }

  const activateDemo = (reason?: string) => {
    const demoIncidents = demoState.incidents.filter((incident) => incidentMatchesFilters(incident, incidentFilters))
    const selectedId = demoIncidents[0]?.id ?? null
    const demoEvidence = selectedId ? demoEvidenceByIncident[selectedId] ?? { items: [], previewUrls: {} } : { items: [], previewUrls: {} }

    setMode('demo')
    setMeData(demoState.me)
    setIncidents(demoIncidents)
    setOperationsCatalog(demoOperationsCatalog)
    setSelectedIncidentId(selectedId)
    setAuditLog(selectedId ? demoState.auditLogs[selectedId] ?? [] : [])
    setEvidenceItems(demoEvidence.items)
    setSelectedEvidenceId(demoEvidence.items[0]?.file_id ?? null)
    setOperationsLoading(false)
    setOperationsError(null)
    setEvidenceLoading(false)
    setEvidenceError(null)
    setEvidenceDownloadUrl(null)
    setEvidenceDownloadLoading(false)
    setEvidenceDownloadError(null)
    setDashboardError(null)
    setBanner(reason ?? 'Modo demonstração local ativo. A API não respondeu neste ambiente.')
    setScreen('dashboard')
    setBooting(false)
  }

  const expireSession = (reason = 'Sessão expirada. Entre novamente para continuar no modo conectado.') => {
    setMode(null)
    setMeData(null)
    setIncidents([])
    setOperationsCatalog(null)
    setSelectedIncidentId(null)
    setAuditLog([])
    setOperationsLoading(false)
    setOperationsError(null)
    setEvidenceItems([])
    setSelectedEvidenceId(null)
    setEvidenceLoading(false)
    setEvidenceError(null)
    setEvidenceDownloadUrl(null)
    setEvidenceDownloadLoading(false)
    setEvidenceDownloadError(null)
    setDashboardError(null)
    setBanner(reason)
    setScreen('login')
    setBooting(false)
  }

  const hydrateLiveDashboard = async (meResponse: MeResponse, preferredIncidentId?: string) => {
    const organization = selectOrganization(meResponse)
    if (!organization) {
      activateDemo('Nenhuma organização ativa encontrada. Exibindo demonstração local.')
      return
    }

    setOperationsLoading(true)
    setOperationsError(null)
    try {
      const operationsResult = await getOperationsCatalog(organization.id).then(
        (result) => ({ status: 'fulfilled' as const, value: result }),
        (reason) => ({ status: 'rejected' as const, reason }),
      )

      if (operationsResult.status === 'fulfilled') {
        setOperationsCatalog(operationsResult.value)
      } else if (isSessionError(operationsResult.reason)) {
        expireSession()
        return
      } else {
        setOperationsCatalog(null)
        setOperationsError(`Não foi possível carregar a configuração operacional: ${normalizeApiError(operationsResult.reason)}`)
      }
      await refreshIncidentList(meResponse, incidentFilters, preferredIncidentId ?? null)
      setScreen('dashboard')
    } catch (error) {
      if (isSessionError(error)) {
        expireSession()
        return
      }
      if (mode === 'demo') {
        setDashboardError('A API falhou durante a atualização. Mantendo a demonstração local.')
        return
      }
      activateDemo(`Modo demonstração local ativado: ${normalizeApiError(error)}`)
    } finally {
      setOperationsLoading(false)
    }
  }

  const loadIncidentContext = async (organizationId: string, incidentId: string) => {
    const requestId = mode === 'demo' ? incidentRequestIdRef.current : ++incidentRequestIdRef.current

    if (mode === 'demo') {
      setSelectedIncidentId(incidentId)
      setAuditLog(demoState.auditLogs[incidentId] ?? [])
      const demoEvidence = demoEvidenceByIncident[incidentId] ?? { items: [], previewUrls: {} }
      setEvidenceItems(demoEvidence.items)
      setSelectedEvidenceId(demoEvidence.items[0]?.file_id ?? null)
      setEvidenceLoading(false)
      setEvidenceError(null)
      setEvidenceDownloadUrl(null)
      setEvidenceDownloadLoading(false)
      setEvidenceDownloadError(null)
      return
    }

    setDashboardLoading(true)
    setDashboardError(null)
    try {
      const [incidentDetail, audit] = await Promise.all([getIncident(organizationId, incidentId), getIncidentAuditLog(organizationId, incidentId, { limit: 50, offset: 0 })])
      if (requestId !== incidentRequestIdRef.current) return
      setIncidents((current) => current.map((incident) => (incident.id === incidentDetail.id ? incidentDetail : incident)))
      setSelectedIncidentId(incidentDetail.id)
      setAuditLog(audit.items ?? [])
      await loadEvidenceContext(organizationId, incidentDetail.id, requestId)
    } catch (error) {
      if (isSessionError(error)) {
        expireSession()
        return
      }
      activateDemo(`Modo demonstração local ativado: ${normalizeApiError(error)}`)
    } finally {
      if (requestId === incidentRequestIdRef.current) {
        setDashboardLoading(false)
      }
    }
  }

  const loadEvidenceContext = async (organizationId: string, incidentId: string, requestId?: number) => {
    setEvidenceLoading(true)
    setEvidenceError(null)
    setEvidenceDownloadError(null)
    setEvidenceDownloadUrl(null)

    try {
      if (mode === 'demo') {
        const demoEvidence = demoEvidenceByIncident[incidentId] ?? { items: [], previewUrls: {} }
        setEvidenceItems(demoEvidence.items)
        setSelectedEvidenceId(demoEvidence.items[0]?.file_id ?? null)
        return
      }

      const response = await listEvidence(organizationId, incidentId)
      if (requestId !== undefined && requestId !== incidentRequestIdRef.current) return
      const items = response.items ?? []
      setEvidenceItems(items)
      setSelectedEvidenceId(items[0]?.file_id ?? null)
    } catch (error) {
      if (isSessionError(error)) {
        setEvidenceError('Sessão expirada para evidências. Entre novamente para ver os anexos.')
        return
      }
      setEvidenceItems([])
      setSelectedEvidenceId(null)
      setEvidenceError(`Não foi possível carregar as evidências: ${normalizeApiError(error)}`)
    } finally {
      if (requestId === undefined || requestId === incidentRequestIdRef.current) {
        setEvidenceLoading(false)
      }
    }
  }

  const openSelectedEvidence = async () => {
    if (!activeOrganization || !selectedIncident || !selectedEvidence) return

    setEvidenceDownloadLoading(true)
    setEvidenceDownloadError(null)

    try {
      if (mode === 'demo') {
        const preview = demoEvidenceByIncident[selectedIncident.id]?.previewUrls[selectedEvidence.file_id]
        if (!preview) {
          setEvidenceDownloadError('Esta evidência demo não tem pré-visualização segura.')
          return
        }
        setEvidenceDownloadUrl(preview)
        return
      }

      const response = await getEvidenceDownloadUrl(activeOrganization.id, selectedIncident.id, selectedEvidence.file_id)
      setEvidenceDownloadUrl(response.download_url)
    } catch (error) {
      if (isSessionError(error)) {
        expireSession()
        return
      }
      setEvidenceDownloadError(`Não foi possível abrir a evidência: ${normalizeApiError(error)}`)
    } finally {
      setEvidenceDownloadLoading(false)
    }
  }

  const selectEvidence = (fileId: string) => {
    setSelectedEvidenceId(fileId)
    setEvidenceDownloadError(null)
    if (fileId !== selectedEvidenceId) {
      setEvidenceDownloadUrl(null)
    }
  }

  const handleAction = async (action: 'acknowledge' | 'resolve' | 'dismiss') => {
    if (!activeOrganization || !selectedIncident) return
    setActionBusy(action)
    setDashboardError(null)

    try {
      if (mode === 'demo') {
        const nextStatus: IncidentStatus = action === 'acknowledge' ? 'acknowledged' : action === 'resolve' ? 'resolved' : 'dismissed'
        const updated: Incident = {
          ...selectedIncident,
          status: nextStatus,
          updated_at: new Date().toISOString(),
          acknowledged_at: nextStatus === 'acknowledged' ? new Date().toISOString() : selectedIncident.acknowledged_at,
          resolved_at: nextStatus === 'resolved' ? new Date().toISOString() : selectedIncident.resolved_at,
          dismissed_at: nextStatus === 'dismissed' ? new Date().toISOString() : selectedIncident.dismissed_at,
        }
        setIncidents((current) => current.map((incident) => (incident.id === updated.id ? updated : incident)))
        setAuditLog((current) => [
          {
            id: `demo-${Date.now()}`,
            organization_id: demoOrganization.id,
            incident_id: updated.id,
            action: `incident.${nextStatus}`,
            from_status: selectedIncident.status,
            to_status: nextStatus,
            actor: 'operator',
            created_at: updated.updated_at,
            metadata: { source: 'demo' },
          },
          ...current,
        ])
        setSelectedIncidentId(updated.id)
        return
      }

      const updated = action === 'acknowledge'
        ? await acknowledgeIncident(activeOrganization.id, selectedIncident.id)
        : action === 'resolve'
          ? await resolveIncident(activeOrganization.id, selectedIncident.id)
          : await dismissIncident(activeOrganization.id, selectedIncident.id)

      setIncidents((current) => current.map((incident) => (incident.id === updated.id ? updated : incident)))
      await loadIncidentContext(activeOrganization.id, updated.id)
    } catch (error) {
      if (isSessionError(error)) {
        expireSession()
        return
      }
      activateDemo(`Modo demonstração local ativado: ${normalizeApiError(error)}`)
    } finally {
      setActionBusy(null)
    }
  }

  const handleLogin = async (options: { forceDemo?: boolean; email?: string; password?: string } = {}) => {
    const email = options.email ?? loginEmail.trim()
    const password = options.password ?? loginPassword
    const forceDemo = options.forceDemo ?? false

    setLoginError(null)
    setLoginLoading(true)

    try {
      if (forceDemo) throw new Error('demo')

      const loginResponse = await login({ email, password })
      const meResponse = await me().catch(() => loginResponse.me)
      setBanner(null)
      await hydrateLiveDashboard(meResponse)
    } catch (error) {
      const shouldFallbackToDemo = forceDemo || email === demoEmail || password === demoPassword || !isApiError(error)
      if (shouldFallbackToDemo) {
        activateDemo('Modo demonstração local ativado. API indisponível ou bloqueada neste ambiente.')
      } else {
        setLoginError(error instanceof Error ? error.message : 'Não foi possível entrar.')
      }
    } finally {
      setLoginLoading(false)
    }
  }

  const updateIncidentFilters = (patch: Partial<IncidentFilters>) => {
    const nextFilters = normalizeIncidentFilters({ ...incidentFilters, ...patch })
    const nextSelectedIncident = selectedIncident

    if (nextSelectedIncident && !incidentMatchesFilters(nextSelectedIncident, nextFilters)) {
      setSelectedIncidentId(null)
      setAuditLog([])
      clearIncidentDetailState()
    }

    setIncidentFilters(nextFilters)
    if (meData) {
      void refreshIncidentList(meData, nextFilters, selectedIncidentId)
    } else {
      writeIncidentFiltersToUrl(nextFilters)
    }
  }

  const resetIncidentFilters = () => {
    updateIncidentFilters({
      status: 'all',
      severity: 'all',
      siteId: 'all',
      cameraId: 'all',
      zoneId: 'all',
      period: 'all',
      createdFrom: '',
      createdTo: '',
    })
  }

  useEffect(() => {
    let cancelled = false

    async function bootstrap() {
      try {
        const meResponse = await me()
        if (cancelled) return
        setMeData(meResponse)
        await hydrateLiveDashboard(meResponse)
      } catch {
        if (!cancelled) setBooting(false)
      }
    }

    bootstrap()
    return () => {
      cancelled = true
    }
  }, [])

  const statusSummary = [
    { label: 'Total', value: incidentSummary.total },
    { label: 'Abertos', value: incidentSummary.open },
    { label: 'Resolvidos', value: incidentSummary.resolved },
  ]

  const liveLabel = mode === 'live' ? 'Conectado à API' : mode === 'demo' ? 'Modo demonstração local' : 'Aguardando conexão'

  return (
    <main className="relative min-h-screen bg-[var(--bg)] text-[var(--ink)]">
      {screen === 'landing' && (
        <div className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col px-5 sm:px-6 lg:px-8">
          <header className="reveal flex items-center justify-between gap-4 border-b border-[color:var(--line)] py-5">
            <button type="button" onClick={() => scrollToSection('top')} className="text-left">
              <Logo size="md" markClassName="h-9 w-9" />
            </button>

            <nav className="hidden items-center gap-8 text-[15px] text-[#57524b] md:flex">
              {navItems.map((item) => (
                <button key={item.id} type="button" onClick={() => scrollToSection(item.id)} className="transition hover:text-[var(--ink)]">
                  {item.label}
                </button>
              ))}
            </nav>

            <div className="flex items-center gap-3 sm:gap-5">
              <button type="button" onClick={() => setScreen('login')} className="text-[15px] font-medium text-[var(--ink)] transition hover:text-[var(--accent)]">
                Entrar
              </button>
              <button type="button" onClick={() => setScreen('login')} className="rounded-lg bg-[var(--ink)] px-4 py-2.5 text-[15px] font-medium text-[var(--paper)] transition hover:bg-[var(--ink-soft)]">
                Solicitar demonstração
              </button>
            </div>
          </header>

          <section id="top" className="flex flex-1 flex-col items-center justify-center py-24 text-center lg:py-32">
            <p className="reveal font-mono-ui text-xs uppercase tracking-[0.24em] text-[var(--muted-2)]">
              Segurança do trabalho · visão computacional
            </p>
            <h1 className="reveal mt-8 max-w-[15ch] font-display text-5xl font-bold leading-[0.98] tracking-[-0.04em] text-[var(--ink)] sm:text-6xl lg:text-7xl" style={{ animationDelay: '120ms' }}>
              Enxergue o risco antes do acidente
            </h1>
            <p className="reveal mt-7 max-w-[600px] text-lg leading-relaxed text-[var(--muted)] sm:text-xl" style={{ animationDelay: '220ms' }}>
              Visão computacional na borda transforma eventos de risco em incidentes auditáveis — com evidências privadas e isolamento por organização.
            </p>
            <div className="reveal mt-11 flex flex-wrap items-center justify-center gap-6" style={{ animationDelay: '320ms' }}>
              <button type="button" onClick={() => setScreen('login')} className="rounded-lg bg-[var(--accent)] px-7 py-3.5 text-base font-semibold text-white transition hover:bg-[var(--accent-hover)]">
                Solicitar demonstração
              </button>
              <button type="button" onClick={() => scrollToSection('como-funciona')} className="inline-flex items-center gap-2 text-base font-medium text-[var(--ink)] transition hover:text-[var(--accent)]">
                Ver como funciona
                <span className="font-mono-ui text-[var(--accent)]">→</span>
              </button>
            </div>
          </section>

          <section id="produto" className="grid gap-5 border-t border-[color:var(--line)] py-16 lg:grid-cols-3">
            {features.map((feature, index) => (
              <article key={feature.title} className="reveal rounded-2xl border border-[color:var(--line)] bg-[var(--card)] p-6" style={{ animationDelay: `${100 * (index + 1)}ms` }}>
                <p className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-[var(--accent)]">{feature.eyebrow}</p>
                <h3 className="mt-3 font-display text-xl font-semibold text-[var(--ink)]">{feature.title}</h3>
                <p className="mt-2.5 text-sm leading-6 text-[var(--muted)]">{feature.description}</p>
              </article>
            ))}
          </section>

          <section id="como-funciona" className="border-t border-[color:var(--line)] py-16">
            <div className="max-w-2xl">
              <p className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-[var(--accent)]">Como funciona</p>
              <h2 className="mt-3 font-display text-3xl font-bold tracking-[-0.02em] text-[var(--ink)] md:text-4xl">Da câmera ao incidente auditável</h2>
              <p className="mt-4 text-base leading-7 text-[var(--muted)]">
                Fluxo direto: detecção na borda, triagem no dashboard e registro completo para auditoria.
              </p>
            </div>
            <ol className="mt-10 grid gap-4 md:grid-cols-3">
              {flowSteps.map((step, index) => (
                <li key={step.title} className="reveal rounded-2xl border border-[color:var(--line)] bg-[var(--card)] p-6" style={{ animationDelay: `${100 * (index + 1)}ms` }}>
                  <span className="font-mono-ui text-sm text-[var(--accent)]">0{index + 1}</span>
                  <h3 className="mt-3 font-display text-lg font-semibold text-[var(--ink)]">{step.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{step.text}</p>
                </li>
              ))}
            </ol>
          </section>

          <section id="seguranca" className="border-t border-[color:var(--line)] py-16">
            <div className="max-w-2xl">
              <p className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-[var(--accent)]">Segurança e privacidade</p>
              <h2 className="mt-3 font-display text-3xl font-bold tracking-[-0.02em] text-[var(--ink)] md:text-4xl">Feito para segurança do trabalho, não para vigilância</h2>
              <p className="mt-4 text-base leading-7 text-[var(--muted)]">
                Privacidade desde a fundação: mínimo necessário de dados, evidências isoladas por organização e trilha auditável.
              </p>
            </div>
            <div className="mt-10 grid gap-4 sm:grid-cols-2">
              {securityPoints.map((point) => (
                <article key={point.title} className="rounded-2xl border border-[color:var(--line)] bg-[var(--card)] p-6">
                  <h3 className="font-display text-lg font-semibold text-[var(--ink)]">{point.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{point.text}</p>
                </article>
              ))}
            </div>
          </section>

          <footer className="flex flex-col items-center gap-4 border-t border-[color:var(--line)] py-8 text-sm text-[var(--muted)] sm:flex-row sm:justify-between">
            <div className="flex items-center gap-2.5">
              <MonogramMark className="h-6 w-6" />
              <span>VigIA Safety · segurança industrial assistida por visão computacional.</span>
            </div>
            <button type="button" onClick={() => setScreen('login')} className="font-medium text-[var(--ink)] transition hover:text-[var(--accent)]">
              Entrar
            </button>
          </footer>
        </div>
      )}

      {screen === 'login' && (
        <div className="relative mx-auto flex min-h-screen w-full max-w-5xl flex-col px-5 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <button type="button" onClick={goLanding} className="text-sm font-medium text-[var(--muted)] transition hover:text-[var(--ink)]">
              ← Voltar à página inicial
            </button>
          </div>

          <div className="flex flex-1 items-center justify-center pb-20">
            <div className="reveal w-full max-w-[360px]">
              <button type="button" onClick={goLanding} className="mx-auto mb-9 flex flex-col items-center gap-3">
                <MonogramMark className="h-11 w-11" />
                <span className="flex flex-col items-center leading-none">
                  <span className="text-lg font-semibold tracking-[0.03em] text-[var(--ink)]">VIGIA</span>
                  <span className="mt-1 font-mono-ui text-[8px] uppercase tracking-[0.34em] text-[var(--label)]">SAFETY</span>
                </span>
              </button>

              <h1 className="text-center font-display text-3xl font-bold tracking-[-0.02em] text-[var(--ink)]">Entrar</h1>
              <p className="mt-1.5 text-center text-sm text-[var(--muted)]">Acesso à plataforma de segurança operacional.</p>

              <form className="mt-8 space-y-4" onSubmit={(event) => { event.preventDefault(); void handleLogin() }}>
                <div>
                  <label htmlFor="login-email" className="mb-1.5 block text-[13px] font-medium text-[#403933]">E-mail</label>
                  <input id="login-email" type="email" value={loginEmail} onChange={(event) => setLoginEmail(event.target.value)} className="h-12 w-full rounded-[10px] border border-[#dcd7cc] bg-[var(--card)] px-3.5 text-[15px] text-[var(--ink)] outline-none transition placeholder:text-[#a09a8e] focus:border-[var(--accent)] focus:ring-2 focus:ring-[rgba(193,85,43,0.16)]" placeholder="voce@empresa.com" />
                </div>
                <div>
                  <div className="mb-1.5 flex items-center justify-between">
                    <label htmlFor="login-password" className="text-[13px] font-medium text-[#403933]">Senha</label>
                    <button type="button" className="text-[13px] text-[var(--accent)] transition hover:opacity-80">Esqueci minha senha</button>
                  </div>
                  <input id="login-password" type="password" value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} className="h-12 w-full rounded-[10px] border border-[#dcd7cc] bg-[var(--card)] px-3.5 text-[15px] text-[var(--ink)] outline-none transition placeholder:text-[#a09a8e] focus:border-[var(--accent)] focus:ring-2 focus:ring-[rgba(193,85,43,0.16)]" placeholder="••••••••••" />
                </div>

                <button type="submit" disabled={loginLoading} className="mt-2 h-12 w-full rounded-[10px] bg-[var(--accent)] text-[15px] font-semibold text-white transition hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-60">
                  {loginLoading ? 'Entrando…' : 'Entrar'}
                </button>

                {loginError ? <p className="rounded-[10px] border border-[rgba(193,85,43,0.2)] bg-[rgba(193,85,43,0.08)] px-3.5 py-2.5 text-[13px] text-[#9e4120]">{loginError}</p> : null}
              </form>

              <p className="mt-7 text-center text-[13px] text-[var(--label)]">Acesso restrito a usuários autorizados.</p>

              <div className="mt-4 flex items-center justify-center gap-3 text-[13px] text-[var(--muted)]">
                <button type="button" onClick={() => void handleLogin({ email: 'admin@vigia.local', password: 'change-me-dev' })} className="transition hover:text-[var(--ink)]">
                  Entrar com demo
                </button>
                <span className="text-[var(--label)]">·</span>
                <button type="button" onClick={() => void handleLogin({ forceDemo: true })} className="transition hover:text-[var(--ink)]">
                  Modo local
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {screen === 'dashboard' && (
        <div className="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-5 sm:px-6 lg:px-8">
          <header className="reveal flex flex-wrap items-center justify-between gap-4 rounded-[28px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.76)] px-4 py-4 shadow-[0_20px_60px_rgba(32,27,24,0.08)] backdrop-blur-sm sm:px-5">
            <button type="button" onClick={goLanding} className="flex items-center gap-3 text-left">
              <span className="grid h-11 w-11 place-items-center rounded-2xl border border-[color:var(--line)] bg-[var(--paper)] text-[var(--ink)] shadow-[0_10px_30px_rgba(32,27,24,0.08)]">
                <MonogramMark className="h-6 w-6" />
              </span>
              <span>
                <span className="block font-display text-lg leading-none tracking-[0.08em]">VigIA</span>
                <span className="mt-1 block text-[11px] uppercase tracking-[0.28em] text-[var(--muted)]">Painel operacional</span>
              </span>
            </button>

            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-[color:var(--line)] bg-[rgba(255,255,255,0.5)] px-4 py-2 text-xs uppercase tracking-[0.24em] text-[var(--muted)]">{liveLabel}</span>
              <button type="button" onClick={() => { setScreen('landing'); setBanner(null) }} className="rounded-full border border-[color:var(--line)] bg-[var(--ink)] px-4 py-2 text-sm font-medium text-[var(--paper)] transition hover:-translate-y-0.5">
                Voltar à landing
              </button>
            </div>
          </header>

          {banner ? <div className="reveal mt-4 rounded-[24px] border border-[rgba(47,125,87,0.2)] bg-[rgba(47,125,87,0.08)] px-4 py-3 text-sm text-[#236444]">{banner}</div> : null}
          {dashboardError ? <div className="reveal mt-4 rounded-[24px] border border-[rgba(193,85,43,0.2)] bg-[rgba(193,85,43,0.08)] px-4 py-3 text-sm text-[#9e4120]">{dashboardError}</div> : null}

          <section className="reveal mt-6 rounded-[34px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.82)] p-6 shadow-[0_22px_60px_rgba(32,27,24,0.08)]" style={{ animationDelay: '60ms' }}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <SectionHeading
                eyebrow="Operação"
                title="Configuração operacional do tenant ativo"
                description="Cada bloco abaixo deixa explícitos os IDs que o edge worker precisa enviar e o contexto ligado a regras e EPI."
              />
              <div className="rounded-[24px] border border-[color:var(--line)] bg-[var(--paper)] px-4 py-3 text-right">
                <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[var(--muted)]">Tenant</p>
                <p className="mt-2 font-display text-lg text-[var(--ink)]">{activeOrganization?.name ?? 'Organização ativa'}</p>
                <p className="text-xs text-[var(--muted)]">{operationsCatalog ? 'Catálogo carregado' : operationsLoading ? 'Carregando catálogo…' : 'Catálogo indisponível'}</p>
              </div>
            </div>

            {operationsError ? (
              <div className="mt-5 rounded-[24px] border border-[rgba(193,85,43,0.2)] bg-[rgba(193,85,43,0.08)] px-4 py-3 text-sm text-[#9e4120]">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p>{operationsError}</p>
                  <button type="button" onClick={() => meData && void hydrateLiveDashboard(meData, selectedIncidentId ?? undefined)} className="font-medium text-[var(--ink)] underline decoration-[rgba(32,27,24,0.3)] underline-offset-4 transition hover:opacity-80">
                    Tentar atualizar
                  </button>
                </div>
              </div>
            ) : null}

            <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              {[
                ['Sites', operationSites.length, 'site_id']
                , ['Câmeras', operationCameras.length, 'camera_id']
                , ['Zonas', operationZones.length, 'zone_id']
                , ['Regras', operationRules.length, 'safety_rule']
                , ['EPI', operationPpe.length, 'required_ppe']
              ].map(([label, value, hint]) => (
                <article key={label} className="rounded-[24px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.58)] p-4">
                  <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[var(--muted)]">{label}</p>
                  <p className="mt-3 font-display text-3xl text-[var(--ink)]">{String(value)}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.22em] text-[var(--muted)]">{hint}</p>
                </article>
              ))}
            </div>

            {operationsLoading && !operationsCatalog ? (
              <div className="mt-6 rounded-[28px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.55)] p-6 text-sm text-[var(--muted)]">
                Carregando configuração operacional…
              </div>
            ) : operationSites.length === 0 ? (
              <div className="mt-6 rounded-[28px] border border-dashed border-[color:var(--line)] bg-[rgba(255,255,255,0.55)] p-6">
                <div className="max-w-2xl space-y-3">
                  <p className="font-display text-2xl text-[var(--ink)]">Nenhum site configurado para este tenant.</p>
                  <p className="text-sm leading-7 text-[var(--muted)]">Para preparar o piloto, cadastre um site, conecte ao menos uma câmera, desenhe as zonas e associe as regras e os EPIs. O worker só consegue operar com <span className="font-medium text-[var(--ink)]">site_id</span>, <span className="font-medium text-[var(--ink)]">camera_id</span> e <span className="font-medium text-[var(--ink)]">zone_id</span> válidos.</p>
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    {['Criar site', 'Vincular câmera', 'Desenhar zona', 'Ligar regra e EPI'].map((step, index) => (
                      <div key={step} className="rounded-[22px] border border-[color:var(--line)] bg-[var(--paper)] px-4 py-3 text-sm text-[var(--ink)]">
                        <p className="font-mono-ui text-[10px] uppercase tracking-[0.24em] text-[var(--muted)]">Passo {index + 1}</p>
                        <p className="mt-2">{step}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-6 grid gap-4 xl:grid-cols-2">
                {operationSites.map((site) => {
                  const siteCameras = operationCameras.filter((camera) => camera.site_id === site.id)
                  const siteZones = operationZones.filter((zone) => zone.site_id === site.id)
                  const siteRules = operationRules.filter((rule) => rule.site_id === site.id || (rule.zone_id ? siteZones.some((zone) => zone.id === rule.zone_id) : false))
                  const sitePpe = operationPpe.filter((item) => item.site_id === site.id || (item.zone_id ? siteZones.some((zone) => zone.id === item.zone_id) : false))

                  return (
                    <article key={site.id} className="rounded-[30px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.62)] p-5 shadow-[0_16px_40px_rgba(32,27,24,0.06)]">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[var(--muted)]">site_id</p>
                          <h3 className="mt-2 font-display text-2xl text-[var(--ink)]">{site.name}</h3>
                          <p className="mt-2 text-sm text-[var(--muted)]">{site.id}{site.address ? ` · ${site.address}` : ''}</p>
                        </div>
                        <OperationStatusPill status={site.status} />
                      </div>

                      <div className="mt-4 grid gap-3 sm:grid-cols-3">
                        <div className="rounded-[20px] border border-[color:var(--line)] bg-[var(--paper)] p-3">
                          <p className="font-mono-ui text-[10px] uppercase tracking-[0.24em] text-[var(--muted)]">Câmeras</p>
                          <p className="mt-2 text-lg font-semibold text-[var(--ink)]">{siteCameras.length}</p>
                        </div>
                        <div className="rounded-[20px] border border-[color:var(--line)] bg-[var(--paper)] p-3">
                          <p className="font-mono-ui text-[10px] uppercase tracking-[0.24em] text-[var(--muted)]">Zonas</p>
                          <p className="mt-2 text-lg font-semibold text-[var(--ink)]">{siteZones.length}</p>
                        </div>
                        <div className="rounded-[20px] border border-[color:var(--line)] bg-[var(--paper)] p-3">
                          <p className="font-mono-ui text-[10px] uppercase tracking-[0.24em] text-[var(--muted)]">Regras / EPI</p>
                          <p className="mt-2 text-lg font-semibold text-[var(--ink)]">{siteRules.length} / {sitePpe.length}</p>
                        </div>
                      </div>

                      <div className="mt-4 space-y-4">
                        <div className="rounded-[24px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.72)] p-4">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="font-display text-lg text-[var(--ink)]">Câmeras vinculadas</p>
                            <p className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-[var(--muted)]">camera_id · site_id</p>
                          </div>
                          <div className="mt-3 space-y-2">
                            {siteCameras.length === 0 ? (
                              <p className="text-sm text-[var(--muted)]">Nenhuma câmera vinculada a este site.</p>
                            ) : siteCameras.map((camera) => (
                              <div key={camera.id} className="flex flex-wrap items-center justify-between gap-3 rounded-[18px] border border-[color:var(--line)] bg-[var(--paper)] px-4 py-3">
                                <div>
                                  <p className="font-medium text-[var(--ink)]">{camera.name}</p>
                                  <p className="mt-1 text-xs text-[var(--muted)]">{camera.id} · {camera.site_id}</p>
                                </div>
                                <OperationStatusPill status={camera.status} />
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="rounded-[24px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.72)] p-4">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="font-display text-lg text-[var(--ink)]">Zonas e worker IDs</p>
                            <p className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-[var(--muted)]">zone_id · camera_id</p>
                          </div>
                          <div className="mt-3 space-y-2">
                            {siteZones.length === 0 ? (
                              <p className="text-sm text-[var(--muted)]">Nenhuma zona cadastrada para este site.</p>
                            ) : siteZones.map((zone) => (
                              <div key={zone.id} className="flex flex-wrap items-center justify-between gap-3 rounded-[18px] border border-[color:var(--line)] bg-[var(--paper)] px-4 py-3">
                                <div>
                                  <div className="flex flex-wrap items-center gap-2">
                                    <p className="font-medium text-[var(--ink)]">{zone.id}</p>
                                    <ZoneTypePill zoneType={zone.zone_type} />
                                  </div>
                                  <p className="mt-1 text-xs text-[var(--muted)]">camera_id {zone.camera_id} · site_id {zone.site_id}</p>
                                </div>
                                <OperationStatusPill status={zone.status} />
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="grid gap-4 md:grid-cols-2">
                          <div className="rounded-[24px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.72)] p-4">
                            <p className="font-display text-lg text-[var(--ink)]">Regras associadas</p>
                            <div className="mt-3 space-y-2">
                              {siteRules.length === 0 ? (
                                <p className="text-sm text-[var(--muted)]">Sem regra ligada a este site.</p>
                              ) : siteRules.map((rule) => (
                                <div key={rule.id} className="rounded-[18px] border border-[color:var(--line)] bg-[var(--paper)] px-4 py-3">
                                  <div className="flex flex-wrap items-center justify-between gap-2">
                                    <p className="font-medium text-[var(--ink)]">{rule.name}</p>
                                    <OperationStatusPill status={rule.status} />
                                  </div>
                                  <p className="mt-1 text-xs text-[var(--muted)]">rule_id {rule.id}{rule.zone_id ? ` · zone_id ${rule.zone_id}` : ''}</p>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="rounded-[24px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.72)] p-4">
                            <p className="font-display text-lg text-[var(--ink)]">EPI requerido</p>
                            <div className="mt-3 space-y-2">
                              {sitePpe.length === 0 ? (
                                <p className="text-sm text-[var(--muted)]">Sem EPI configurado para este site.</p>
                              ) : sitePpe.map((item) => (
                                <div key={item.id} className="rounded-[18px] border border-[color:var(--line)] bg-[var(--paper)] px-4 py-3">
                                  <div className="flex flex-wrap items-center justify-between gap-2">
                                    <p className="font-medium text-[var(--ink)]">{item.item}</p>
                                    <OperationStatusPill status={item.status} />
                                  </div>
                                  <p className="mt-1 text-xs text-[var(--muted)]">ppe_id {item.id} · rule_id {item.rule_id}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    </article>
                  )
                })}
              </div>
            )}
          </section>

          <section className="mt-6 grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
            <div className="space-y-6">
              <section className="reveal rounded-[34px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.8)] p-6 shadow-[0_22px_60px_rgba(32,27,24,0.08)]" style={{ animationDelay: '80ms' }}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="font-mono-ui text-[11px] uppercase tracking-[0.3em] text-[var(--muted)]">{activeOrganization ? activeOrganization.name : 'Organização ativa'}</p>
                    <h1 className="mt-3 font-display text-3xl leading-tight text-[var(--ink)] sm:text-4xl">Dashboard conectado à API</h1>
                    <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--muted)]">A lista abaixo vem da organização ativa. Se a API falhar, o painel entra em demonstração local sem quebrar a navegação.</p>
                  </div>
                  <div className="rounded-[24px] border border-[color:var(--line)] bg-[var(--paper)] px-4 py-3 text-right">
                    <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[var(--muted)]">Sessão</p>
                    <p className="mt-2 font-display text-lg text-[var(--ink)]">{meData?.user.full_name ?? meData?.user.email ?? '—'}</p>
                    <p className="text-xs text-[var(--muted)]">{meData?.user.email ?? '—'}</p>
                  </div>
                </div>

                <div className="mt-6 grid gap-3 sm:grid-cols-3">
                  {statusSummary.map((item) => (
                    <article key={item.label} className="rounded-[24px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.58)] p-4">
                      <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[var(--muted)]">{item.label}</p>
                      <p className="mt-3 font-display text-3xl text-[var(--ink)]">{item.value}</p>
                    </article>
                  ))}
                </div>

                {dashboardLoading ? <p className="mt-5 text-sm text-[var(--muted)]">Atualizando dados do painel…</p> : null}
              </section>

              <section className="reveal rounded-[34px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.8)] p-6 shadow-[0_22px_60px_rgba(32,27,24,0.08)]" style={{ animationDelay: '140ms' }}>
                <SectionHeading eyebrow="Incidentes" title="Lista operacional" description="Selecione um incidente para ver o detalhe completo, auditoria e ações disponíveis." />

                <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2 text-sm text-[var(--muted)]">
                    <span className="rounded-full border border-[color:var(--line)] bg-[rgba(255,255,255,0.55)] px-3 py-1">{incidentSummary.total} registros</span>
                    {hasActiveIncidentFilters ? <span className="rounded-full border border-[rgba(193,85,43,0.18)] bg-[rgba(193,85,43,0.08)] px-3 py-1 text-[#9e4120]">Filtros ativos</span> : null}
                    {dashboardLoading ? <span className="rounded-full border border-[color:var(--line)] bg-[rgba(255,255,255,0.55)] px-3 py-1">Atualizando…</span> : null}
                  </div>
                  <button type="button" onClick={resetIncidentFilters} className="rounded-full border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-2 text-sm font-medium text-[var(--ink)] transition hover:-translate-y-0.5 hover:bg-white">
                    Limpar filtros
                  </button>
                </div>

                <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-6">
                  <label className="block space-y-2">
                    <span className="text-[11px] uppercase tracking-[0.24em] text-[var(--muted)]">Status</span>
                    <select value={incidentFilters.status} onChange={(event) => updateIncidentFilters({ status: event.target.value as IncidentStatus | 'all' })} className="w-full rounded-2xl border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-3 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[rgba(193,85,43,0.55)] focus:ring-4 focus:ring-[rgba(193,85,43,0.12)]">
                      <option value="all">Todos</option>
                      <option value="open">Aberto</option>
                      <option value="acknowledged">Reconhecido</option>
                      <option value="resolved">Resolvido</option>
                      <option value="dismissed">Descartado</option>
                    </select>
                  </label>

                  <label className="block space-y-2">
                    <span className="text-[11px] uppercase tracking-[0.24em] text-[var(--muted)]">Severidade</span>
                    <select value={incidentFilters.severity} onChange={(event) => updateIncidentFilters({ severity: event.target.value })} className="w-full rounded-2xl border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-3 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[rgba(193,85,43,0.55)] focus:ring-4 focus:ring-[rgba(193,85,43,0.12)]">
                      <option value="all">Todas</option>
                      {Array.from(new Set(['high', 'medium', 'low', ...incidents.map((incident) => incident.severity.toLowerCase())]))
                        .filter((value, index, list) => list.indexOf(value) === index)
                        .map((value) => (
                          <option key={value} value={value} className="capitalize">
                            {value === 'high' ? 'Alta' : value === 'medium' ? 'Média' : value === 'low' ? 'Baixa' : value}
                          </option>
                        ))}
                    </select>
                  </label>

                  <label className="block space-y-2">
                    <span className="text-[11px] uppercase tracking-[0.24em] text-[var(--muted)]">Site</span>
                    <select value={incidentFilters.siteId} onChange={(event) => updateIncidentFilters({ siteId: event.target.value, cameraId: 'all', zoneId: 'all' })} disabled={operationsLoading && !operationsCatalog} className="w-full rounded-2xl border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-3 py-3 text-sm text-[var(--ink)] outline-none transition disabled:cursor-not-allowed disabled:opacity-60 focus:border-[rgba(193,85,43,0.55)] focus:ring-4 focus:ring-[rgba(193,85,43,0.12)]">
                      <option value="all">Todos</option>
                      {filteredSiteOptions.map((site) => (
                        <option key={site.id} value={site.id}>{site.name} · {site.id}</option>
                      ))}
                    </select>
                  </label>

                  <label className="block space-y-2">
                    <span className="text-[11px] uppercase tracking-[0.24em] text-[var(--muted)]">Câmera</span>
                    <select value={incidentFilters.cameraId} onChange={(event) => updateIncidentFilters({ cameraId: event.target.value, zoneId: 'all' })} disabled={operationsLoading && !operationsCatalog} className="w-full rounded-2xl border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-3 py-3 text-sm text-[var(--ink)] outline-none transition disabled:cursor-not-allowed disabled:opacity-60 focus:border-[rgba(193,85,43,0.55)] focus:ring-4 focus:ring-[rgba(193,85,43,0.12)]">
                      <option value="all">Todas</option>
                      {filteredCameraOptions.map((camera) => (
                        <option key={camera.id} value={camera.id}>{camera.name} · {camera.id}</option>
                      ))}
                    </select>
                  </label>

                  <label className="block space-y-2">
                    <span className="text-[11px] uppercase tracking-[0.24em] text-[var(--muted)]">Zona</span>
                    <select value={incidentFilters.zoneId} onChange={(event) => updateIncidentFilters({ zoneId: event.target.value })} disabled={operationsLoading && !operationsCatalog} className="w-full rounded-2xl border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-3 py-3 text-sm text-[var(--ink)] outline-none transition disabled:cursor-not-allowed disabled:opacity-60 focus:border-[rgba(193,85,43,0.55)] focus:ring-4 focus:ring-[rgba(193,85,43,0.12)]">
                      <option value="all">Todas</option>
                      {filteredZoneOptions.map((zone) => (
                        <option key={zone.id} value={zone.id}>{zone.id} · {zone.zone_type}</option>
                      ))}
                    </select>
                  </label>

                  <label className="block space-y-2">
                    <span className="text-[11px] uppercase tracking-[0.24em] text-[var(--muted)]">Período</span>
                    <select
                      value={incidentFilters.period}
                      onChange={(event) => {
                        const period = event.target.value as IncidentPeriod
                        if (period === 'all') {
                          updateIncidentFilters({ period: 'all', createdFrom: '', createdTo: '' })
                          return
                        }
                        if (period === 'custom') {
                          const fallback = getPresetRange('7d')
                          updateIncidentFilters({
                            period: 'custom',
                            createdFrom: formatDateInput(incidentFilters.createdFrom) || fallback.createdFrom.slice(0, 10),
                            createdTo: formatDateInput(incidentFilters.createdTo) || fallback.createdTo.slice(0, 10),
                          })
                          return
                        }
                        updateIncidentFilters({ period })
                      }}
                      className="w-full rounded-2xl border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-3 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[rgba(193,85,43,0.55)] focus:ring-4 focus:ring-[rgba(193,85,43,0.12)]"
                    >
                      <option value="all">Todo o período</option>
                      <option value="24h">Últimas 24h</option>
                      <option value="7d">Últimos 7 dias</option>
                      <option value="30d">Últimos 30 dias</option>
                      <option value="custom">Personalizado</option>
                    </select>
                  </label>
                </div>

                {incidentFilters.period === 'custom' ? (
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    <label className="block space-y-2">
                      <span className="text-[11px] uppercase tracking-[0.24em] text-[var(--muted)]">Criado de</span>
                      <input
                        type="date"
                        value={formatDateInput(incidentFilters.createdFrom)}
                        onChange={(event) => updateIncidentFilters({ period: 'custom', createdFrom: event.target.value })}
                        className="w-full rounded-2xl border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-3 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[rgba(193,85,43,0.55)] focus:ring-4 focus:ring-[rgba(193,85,43,0.12)]"
                      />
                    </label>
                    <label className="block space-y-2">
                      <span className="text-[11px] uppercase tracking-[0.24em] text-[var(--muted)]">Criado até</span>
                      <input
                        type="date"
                        value={formatDateInput(incidentFilters.createdTo)}
                        onChange={(event) => updateIncidentFilters({ period: 'custom', createdTo: event.target.value })}
                        className="w-full rounded-2xl border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-3 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[rgba(193,85,43,0.55)] focus:ring-4 focus:ring-[rgba(193,85,43,0.12)]"
                      />
                    </label>
                  </div>
                ) : null}

                <div className="mt-6 space-y-3">
                  {dashboardLoading && incidents.length === 0 ? (
                    <div className="rounded-[28px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.55)] p-6 text-sm text-[var(--muted)]">
                      Carregando incidentes…
                    </div>
                  ) : incidents.length === 0 ? (
                    <div className="rounded-[28px] border border-dashed border-[color:var(--line)] bg-[rgba(255,255,255,0.55)] p-6 text-sm text-[var(--muted)]">
                      {hasActiveIncidentFilters ? (
                        <div className="space-y-2">
                          <p className="font-display text-2xl text-[var(--ink)]">Nenhum incidente encontrou esses filtros.</p>
                          <p>Revise status, severidade, site, câmera, zona ou período para voltar a ver eventos.</p>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <p className="font-display text-2xl text-[var(--ink)]">Nenhum incidente registrado para esta organização.</p>
                          <p>Quando o worker começar a enviar eventos, eles aparecerão aqui com triagem, contexto e auditoria.</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    incidents.map((incident) => (
                      <button
                        key={incident.id}
                        type="button"
                        onClick={() => activeOrganization && void loadIncidentContext(activeOrganization.id, incident.id)}
                        className={`w-full rounded-[28px] border p-4 text-left transition hover:-translate-y-0.5 hover:shadow-[0_16px_36px_rgba(32,27,24,0.08)] ${selectedIncidentId === incident.id ? 'border-[rgba(193,85,43,0.35)] bg-[rgba(193,85,43,0.06)]' : 'border-[color:var(--line)] bg-[rgba(255,255,255,0.55)]'}`}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="font-display text-xl text-[var(--ink)]">{incident.summary}</p>
                              <StatusPill status={incident.status} />
                            </div>
                            <p className="mt-2 text-sm text-[var(--muted)]">
                              {incident.site_id ?? 'Site não informado'} · {incident.camera_id} · Zona {incident.zone_id}
                            </p>
                          </div>
                          <SeverityPill severity={incident.severity} />
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </section>
            </div>

            <div className="space-y-6">
              <section className="reveal rounded-[34px] border border-[color:var(--line)] bg-[rgba(32,27,24,0.96)] p-6 text-[var(--paper)] shadow-[0_26px_80px_rgba(32,27,24,0.18)]" style={{ animationDelay: '120ms' }}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-mono-ui text-[11px] uppercase tracking-[0.3em] text-[rgba(245,243,239,0.7)]">Detalhe do incidente</p>
                    <h2 className="mt-3 font-display text-3xl leading-tight">{selectedIncident?.summary ?? 'Selecione um incidente'}</h2>
                  </div>
                  {selectedIncident ? <StatusPill status={selectedIncident.status} /> : null}
                </div>

                {selectedIncident ? (
                  <div className="mt-6 space-y-5 text-sm leading-7 text-[rgba(245,243,239,0.82)]">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="rounded-[24px] border border-white/10 bg-white/5 p-4">
                        <p className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-[rgba(245,243,239,0.65)]">Site</p>
                        <p className="mt-2 font-display text-lg text-[var(--paper)]">{selectedIncident.site_id ?? '—'}</p>
                      </div>
                      <div className="rounded-[24px] border border-white/10 bg-white/5 p-4">
                        <p className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-[rgba(245,243,239,0.65)]">Câmera</p>
                        <p className="mt-2 font-display text-lg text-[var(--paper)]">{selectedIncident.camera_id}</p>
                      </div>
                      <div className="rounded-[24px] border border-white/10 bg-white/5 p-4">
                        <p className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-[rgba(245,243,239,0.65)]">Severidade</p>
                        <p className="mt-2 font-display text-lg text-[var(--paper)] capitalize">{selectedIncident.severity}</p>
                      </div>
                      <div className="rounded-[24px] border border-white/10 bg-white/5 p-4">
                        <p className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-[rgba(245,243,239,0.65)]">Atualizado</p>
                        <p className="mt-2 font-display text-lg text-[var(--paper)]">{formatTimestamp(selectedIncident.updated_at)}</p>
                      </div>
                    </div>

                    <EvidenceExplorer
                      incident={selectedIncident}
                      organizationName={activeOrganization?.name ?? null}
                      evidenceItems={evidenceItems}
                      selectedEvidence={selectedEvidence}
                      evidenceLoading={evidenceLoading}
                      evidenceError={evidenceError}
                      evidenceDownloadUrl={evidenceDownloadUrl}
                      evidenceDownloadLoading={evidenceDownloadLoading}
                      evidenceDownloadError={evidenceDownloadError}
                      onSelectEvidence={selectEvidence}
                      onOpenEvidence={() => void openSelectedEvidence()}
                      onRetry={() => void loadEvidenceContext(activeOrganization?.id ?? selectedIncident.organization_id, selectedIncident.id)}
                    />

                    <div className="grid gap-3 rounded-[28px] border border-white/10 bg-white/5 p-4 text-[rgba(245,243,239,0.84)] sm:grid-cols-2">
                      <p><span className="text-[rgba(245,243,239,0.6)]">Criado:</span> {formatTimestamp(selectedIncident.created_at)}</p>
                      <p><span className="text-[rgba(245,243,239,0.6)]">Reconhecido:</span> {formatTimestamp(selectedIncident.acknowledged_at)}</p>
                      <p><span className="text-[rgba(245,243,239,0.6)]">Resolvido:</span> {formatTimestamp(selectedIncident.resolved_at)}</p>
                      <p><span className="text-[rgba(245,243,239,0.6)]">Descartado:</span> {formatTimestamp(selectedIncident.dismissed_at)}</p>
                    </div>

                    <div className="flex flex-wrap gap-3 pt-2">
                      <button type="button" disabled={actionBusy !== null} onClick={() => void handleAction('acknowledge')} className="rounded-full bg-[var(--accent)] px-5 py-3 font-medium text-[var(--paper)] shadow-[0_16px_40px_rgba(193,85,43,0.28)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60">
                        {actionBusy === 'acknowledge' ? 'Reconhecendo…' : 'Reconhecer'}
                      </button>
                      <button type="button" disabled={actionBusy !== null} onClick={() => void handleAction('resolve')} className="rounded-full border border-white/10 bg-white/5 px-5 py-3 font-medium text-[var(--paper)] transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60">
                        {actionBusy === 'resolve' ? 'Resolvendo…' : 'Resolver'}
                      </button>
                      <button type="button" disabled={actionBusy !== null} onClick={() => void handleAction('dismiss')} className="rounded-full border border-white/10 bg-white/5 px-5 py-3 font-medium text-[var(--paper)] transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60">
                        {actionBusy === 'dismiss' ? 'Descartando…' : 'Descartar'}
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="mt-6 text-sm leading-7 text-[rgba(245,243,239,0.72)]">Nenhum incidente selecionado.</p>
                )}
              </section>

              <section className="reveal rounded-[34px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.8)] p-6 shadow-[0_22px_60px_rgba(32,27,24,0.08)]" style={{ animationDelay: '200ms' }}>
                <SectionHeading eyebrow="Auditoria" title="Trilha de eventos" description="Cada mudança relevante fica visível para revisão rápida." />
                <div className="mt-6 space-y-3">
                  {auditLog.length === 0 ? (
                    <div className="rounded-[24px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.55)] p-5 text-sm text-[var(--muted)]">Sem registros de auditoria para este incidente.</div>
                  ) : (
                    auditLog.map((entry) => (
                      <article key={entry.id} className="rounded-[24px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.58)] p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="font-display text-lg text-[var(--ink)]">{entry.action}</p>
                            <p className="mt-1 text-sm text-[var(--muted)]">{entry.actor} · {formatTimestamp(entry.created_at)}</p>
                          </div>
                          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">{entry.from_status ?? '—'} → {entry.to_status}</p>
                        </div>
                      </article>
                    ))
                  )}
                </div>
              </section>
            </div>
          </section>

          <footer className="reveal mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-[color:var(--line)] py-6 text-sm text-[var(--muted)]" style={{ animationDelay: '280ms' }}>
            <p>VigIA Safety · {activeOrganization?.name ?? 'Painel operacional'} · {liveLabel}</p>
            <button type="button" onClick={() => void activateDemo('Modo demonstração local reativado manualmente.')} className="font-medium text-[var(--ink)] transition hover:text-[var(--accent)]">
              Reativar demonstração
            </button>
          </footer>
        </div>
      )}

      {booting ? <div className="pointer-events-none fixed bottom-4 right-4 rounded-full border border-[color:var(--line)] bg-[rgba(245,243,239,0.92)] px-4 py-2 text-xs uppercase tracking-[0.24em] text-[var(--muted)] shadow-[0_12px_30px_rgba(32,27,24,0.1)]">Verificando sessão…</div> : null}
    </main>
  )
}
