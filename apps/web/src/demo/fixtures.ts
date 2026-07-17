import type { MeResponse } from '../api/auth'
import type { AuditLogEntry, Incident } from '../api/incidents'
import type { EvidenceItem } from '../api/evidence'
import type { OperationCatalog } from '../api/operations'

export const demoOrganization = { id: 'org-dev', name: 'VigIA Local', slug: 'vigia-local' }
export const demoEmail = 'admin@vigia.local'
export const demoPassword = 'change-me-dev'

const demoMe: MeResponse = {
  user: { id: 'user-dev', email: demoEmail, full_name: 'VigIA Admin' },
  memberships: [{ organization: demoOrganization, role: 'owner', permissions: ['incidents.read', 'incidents.acknowledge', 'incidents.resolve', 'incidents.dismiss', 'audit.read'], active: true }],
  active_organization: demoOrganization,
  active_permissions: ['incidents.read', 'incidents.acknowledge', 'incidents.resolve', 'incidents.dismiss', 'audit.read'],
}

const now = Date.now()
const minutesAgo = (minutes: number) => new Date(now - minutes * 60_000).toISOString()

export const demoState: { me: MeResponse; incidents: Incident[]; auditLogs: Record<string, AuditLogEntry[]> } = {
  me: demoMe,
  incidents: [
    { id: 'inc-demo-1', organization_id: demoOrganization.id, site_id: 'Pátio Sul', detection_event_id: 'evt-demo-1', camera_id: 'cam-07', zone_id: 'zona-armazenagem', worker_id: null, event_type: 'detection', severity: 'high', summary: 'Pessoa próxima à área restrita', confidence: 0.94, metadata: { site_label: 'Pátio Sul', camera_label: 'Câmera 07' }, status: 'open', created_at: minutesAgo(18), updated_at: minutesAgo(18), acknowledged_at: null, resolved_at: null, dismissed_at: null },
    { id: 'inc-demo-2', organization_id: demoOrganization.id, site_id: 'Linha 2', detection_event_id: 'evt-demo-2', camera_id: 'cam-12', zone_id: 'linha-pintura', worker_id: 'worker-11', event_type: 'detection', severity: 'medium', summary: 'Ausência de EPI em zona controlada', confidence: 0.88, metadata: { site_label: 'Linha 2', camera_label: 'Câmera 12' }, status: 'acknowledged', created_at: minutesAgo(42), updated_at: minutesAgo(34), acknowledged_at: minutesAgo(34), resolved_at: null, dismissed_at: null },
    { id: 'inc-demo-3', organization_id: demoOrganization.id, site_id: 'Doca Norte', detection_event_id: 'evt-demo-3', camera_id: 'cam-03', zone_id: 'acesso-veiculos', worker_id: null, event_type: 'detection', severity: 'low', summary: 'Fluxo incomum em passagem de veículos', confidence: 0.79, metadata: { site_label: 'Doca Norte', camera_label: 'Câmera 03' }, status: 'resolved', created_at: minutesAgo(120), updated_at: minutesAgo(92), acknowledged_at: minutesAgo(111), resolved_at: minutesAgo(92), dismissed_at: null },
  ],
  auditLogs: {
    'inc-demo-1': [{ id: 'log-demo-1a', organization_id: demoOrganization.id, incident_id: 'inc-demo-1', action: 'created', from_status: null, to_status: 'open', actor: 'system', created_at: minutesAgo(18), metadata: { source: 'demo' } }],
    'inc-demo-2': [
      { id: 'log-demo-2a', organization_id: demoOrganization.id, incident_id: 'inc-demo-2', action: 'created', from_status: null, to_status: 'open', actor: 'system', created_at: minutesAgo(42), metadata: { source: 'demo' } },
      { id: 'log-demo-2b', organization_id: demoOrganization.id, incident_id: 'inc-demo-2', action: 'incident.acknowledged', from_status: 'open', to_status: 'acknowledged', actor: 'operator', created_at: minutesAgo(34), metadata: { source: 'demo' } },
    ],
    'inc-demo-3': [
      { id: 'log-demo-3a', organization_id: demoOrganization.id, incident_id: 'inc-demo-3', action: 'created', from_status: null, to_status: 'open', actor: 'system', created_at: minutesAgo(120), metadata: { source: 'demo' } },
      { id: 'log-demo-3b', organization_id: demoOrganization.id, incident_id: 'inc-demo-3', action: 'incident.acknowledged', from_status: 'open', to_status: 'acknowledged', actor: 'operator', created_at: minutesAgo(111), metadata: { source: 'demo' } },
      { id: 'log-demo-3c', organization_id: demoOrganization.id, incident_id: 'inc-demo-3', action: 'incident.resolved', from_status: 'acknowledged', to_status: 'resolved', actor: 'operator', created_at: minutesAgo(92), metadata: { source: 'demo' } },
    ],
  },
}

export function createDemoFrame(title: string, label: string, accent: string) {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
      <defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1"><stop offset="0%" stop-color="#0f1419"/><stop offset="100%" stop-color="#1f2933"/></linearGradient></defs>
      <rect width="1280" height="720" fill="url(#g)"/>
      <rect x="84" y="72" width="1112" height="576" rx="34" fill="none" stroke="${accent}" stroke-opacity="0.52" stroke-width="6"/>
      <rect x="104" y="94" width="1068" height="532" rx="26" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.12)"/>
      <circle cx="944" cy="310" r="118" fill="none" stroke="${accent}" stroke-opacity="0.45" stroke-width="12"/>
      <circle cx="944" cy="310" r="42" fill="${accent}" fill-opacity="0.8"/>
      <text x="170" y="170" fill="#f5f3ef" font-family="IBM Plex Sans, Arial" font-size="38" font-weight="600">${title}</text>
      <text x="170" y="344" fill="#d7dde4" font-family="IBM Plex Mono, monospace" font-size="24">${label}</text>
      <text x="170" y="402" fill="#8f9aab" font-family="IBM Plex Sans, Arial" font-size="20">Triagem demo · evidência sintética</text>
    </svg>
  `
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

export const demoEvidenceByIncident: Record<string, { items: EvidenceItem[]; previewUrls: Record<string, string> }> = {
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
        metadata: { confidence: 0.94, model_version: 'real-cv-0.8.2', event_type: 'detection', frame_timestamp: minutesAgo(18), source_type: 'camera', site_id: 'Pátio Sul', camera_id: 'cam-07', zone_id: 'zona-armazenagem', sha256: 'a91f9d1e6c0a5c0f1b3a43eac9f2e1ff9c3f1c2a9f3b71d4b0aaf2a8c5b6e1d9' },
      },
    ],
    previewUrls: { 'ev-demo-1-snapshot': createDemoFrame('Pessoa próxima à área restrita', 'Câmera 07 · Pátio Sul', '#c1552b') },
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
        metadata: { confidence: 0.88, model_version: 'real-cv-0.8.2', event_type: 'detection', frame_timestamp: minutesAgo(42), source_type: 'camera', site_id: 'Linha 2', camera_id: 'cam-12', zone_id: 'linha-pintura', sha256: 'b71e4c3a9f0b2c1d7e3f5a8b9c1d2e3f4a5b6c7d8e9f00112233445566778899' },
      },
    ],
    previewUrls: {},
  },
  'inc-demo-3': { items: [], previewUrls: {} },
}

export const demoOperationsCatalog: OperationCatalog = {
  organization_id: demoOrganization.id,
  sites: [
    { id: 'site-demo-patio-sul', organization_id: demoOrganization.id, name: 'Pátio Sul', address: 'Portaria 2 · área externa', status: 'active', cameras: [{ id: 'camera-demo-07', organization_id: demoOrganization.id, site_id: 'site-demo-patio-sul', name: 'Câmera 07', stream_identifier: 'rtsp://demo/camera-07', status: 'active' }], zones: [{ id: 'zone-demo-armazenagem', organization_id: demoOrganization.id, site_id: 'site-demo-patio-sul', camera_id: 'camera-demo-07', zone_type: 'restricted', status: 'active' }], safety_rules: [{ id: 'rule-demo-helmet', organization_id: demoOrganization.id, site_id: 'site-demo-patio-sul', zone_id: 'zone-demo-armazenagem', name: 'Capacete obrigatório', status: 'active', metadata: { severity: 'high', source: 'demo' } }], required_ppe: [{ id: 'ppe-demo-helmet', organization_id: demoOrganization.id, rule_id: 'rule-demo-helmet', site_id: 'site-demo-patio-sul', zone_id: 'zone-demo-armazenagem', item: 'capacete', status: 'active' }] },
    { id: 'site-demo-linha-2', organization_id: demoOrganization.id, name: 'Linha 2', address: 'Galpão principal · pintura', status: 'active', cameras: [{ id: 'camera-demo-12', organization_id: demoOrganization.id, site_id: 'site-demo-linha-2', name: 'Câmera 12', stream_identifier: 'rtsp://demo/camera-12', status: 'active' }], zones: [{ id: 'zone-demo-pintura', organization_id: demoOrganization.id, site_id: 'site-demo-linha-2', camera_id: 'camera-demo-12', zone_type: 'ppe', status: 'active' }], safety_rules: [{ id: 'rule-demo-oculos', organization_id: demoOrganization.id, site_id: 'site-demo-linha-2', zone_id: 'zone-demo-pintura', name: 'Óculos de proteção', status: 'active', metadata: { severity: 'medium', source: 'demo' } }], required_ppe: [{ id: 'ppe-demo-oculos', organization_id: demoOrganization.id, rule_id: 'rule-demo-oculos', site_id: 'site-demo-linha-2', zone_id: 'zone-demo-pintura', item: 'óculos', status: 'active' }] },
    { id: 'site-demo-doca-norte', organization_id: demoOrganization.id, name: 'Doca Norte', address: 'Recebimento de cargas', status: 'inactive', cameras: [{ id: 'camera-demo-03', organization_id: demoOrganization.id, site_id: 'site-demo-doca-norte', name: 'Câmera 03', stream_identifier: 'rtsp://demo/camera-03', status: 'inactive' }], zones: [{ id: 'zone-demo-veiculos', organization_id: demoOrganization.id, site_id: 'site-demo-doca-norte', camera_id: 'camera-demo-03', zone_type: 'access', status: 'inactive' }], safety_rules: [{ id: 'rule-demo-faixa', organization_id: demoOrganization.id, site_id: 'site-demo-doca-norte', zone_id: 'zone-demo-veiculos', name: 'Área isolada para veículos', status: 'inactive', metadata: { source: 'demo' } }], required_ppe: [{ id: 'ppe-demo-faixa', organization_id: demoOrganization.id, rule_id: 'rule-demo-faixa', site_id: 'site-demo-doca-norte', zone_id: 'zone-demo-veiculos', item: 'faixa refletiva', status: 'inactive' }] },
  ],
  cameras: [{ id: 'camera-demo-07', organization_id: demoOrganization.id, site_id: 'site-demo-patio-sul', name: 'Câmera 07', stream_identifier: 'rtsp://demo/camera-07', status: 'active' }, { id: 'camera-demo-12', organization_id: demoOrganization.id, site_id: 'site-demo-linha-2', name: 'Câmera 12', stream_identifier: 'rtsp://demo/camera-12', status: 'active' }, { id: 'camera-demo-03', organization_id: demoOrganization.id, site_id: 'site-demo-doca-norte', name: 'Câmera 03', stream_identifier: 'rtsp://demo/camera-03', status: 'inactive' }],
  zones: [{ id: 'zone-demo-armazenagem', organization_id: demoOrganization.id, site_id: 'site-demo-patio-sul', camera_id: 'camera-demo-07', zone_type: 'restricted', status: 'active' }, { id: 'zone-demo-pintura', organization_id: demoOrganization.id, site_id: 'site-demo-linha-2', camera_id: 'camera-demo-12', zone_type: 'ppe', status: 'active' }, { id: 'zone-demo-veiculos', organization_id: demoOrganization.id, site_id: 'site-demo-doca-norte', camera_id: 'camera-demo-03', zone_type: 'access', status: 'inactive' }],
  safety_rules: [{ id: 'rule-demo-helmet', organization_id: demoOrganization.id, site_id: 'site-demo-patio-sul', zone_id: 'zone-demo-armazenagem', name: 'Capacete obrigatório', status: 'active', metadata: { severity: 'high', source: 'demo' } }, { id: 'rule-demo-oculos', organization_id: demoOrganization.id, site_id: 'site-demo-linha-2', zone_id: 'zone-demo-pintura', name: 'Óculos de proteção', status: 'active', metadata: { severity: 'medium', source: 'demo' } }, { id: 'rule-demo-faixa', organization_id: demoOrganization.id, site_id: 'site-demo-doca-norte', zone_id: 'zone-demo-veiculos', name: 'Área isolada para veículos', status: 'inactive', metadata: { source: 'demo' } }],
  required_ppe: [{ id: 'ppe-demo-helmet', organization_id: demoOrganization.id, rule_id: 'rule-demo-helmet', site_id: 'site-demo-patio-sul', zone_id: 'zone-demo-armazenagem', item: 'capacete', status: 'active' }, { id: 'ppe-demo-oculos', organization_id: demoOrganization.id, rule_id: 'rule-demo-oculos', site_id: 'site-demo-linha-2', zone_id: 'zone-demo-pintura', item: 'óculos', status: 'active' }, { id: 'ppe-demo-faixa', organization_id: demoOrganization.id, rule_id: 'rule-demo-faixa', site_id: 'site-demo-doca-norte', zone_id: 'zone-demo-veiculos', item: 'faixa refletiva', status: 'inactive' }],
}
