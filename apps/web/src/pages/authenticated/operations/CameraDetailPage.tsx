import { Icon } from '../../../components/ui/icons'
import { LiveCameraPlayer } from '../../../components/operations/LiveCameraPlayer'
import type { Incident } from '../../../api/incidents'
import type { OperationCamera, OperationSite, OperationZone } from '../../../api/operations'

const SEVERITY_TONE: Record<string, { bg: string; color: string }> = {
  high: { bg: '#F7E2DC', color: '#B14A22' },
  medium: { bg: '#F6EBD6', color: '#946416' },
  low: { bg: '#E7F1EB', color: '#1F6B4A' },
}

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const minutes = Math.round(diffMs / 60000)
  if (minutes < 1) return 'agora'
  if (minutes < 60) return `${minutes}min`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h`
  return `${Math.round(hours / 24)}d`
}

function polygonPointsOf(zone: OperationZone): [number, number][] {
  const points = (zone.polygon_json as { points?: [number, number][] } | undefined)?.points
  return Array.isArray(points) ? points : []
}

/**
 * Página da câmera: o ao vivo com a CV trabalhando, as zonas que valem para ela e os
 * incidentes que ela gerou — tudo que o operador precisa sobre uma câmera, num lugar só.
 */
export function CameraDetailPage({
  site,
  camera,
  zones,
  incidents,
  zoneTypeBadge,
  statusBadge,
  onBack,
  onRequestLiveTicket,
  onOpenIncidents,
}: {
  site: OperationSite
  camera: OperationCamera
  zones: OperationZone[]
  incidents: Incident[]
  zoneTypeBadge: Record<string, { label: string; bg: string; color: string }>
  statusBadge: Record<string, { label: string; bg: string; color: string }>
  onBack: () => void
  onRequestLiveTicket?: (cameraId: string) => Promise<{ whep_url: string; token?: string } | null>
  onOpenIncidents: () => void
}) {
  const cameraZones = zones.filter((zone) => zone.camera_id === camera.id)
  const cameraIncidents = incidents.filter((incident) => incident.camera_id === camera.id).slice(0, 6)
  const zonePolygons = cameraZones
    .map((zone) => ({ points: polygonPointsOf(zone), zoneType: zone.zone_type }))
    .filter((zone) => zone.points.length >= 3)
  const badge = statusBadge[camera.status]

  return (
    <div className="space-y-3.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <button type="button" onClick={onBack} className="mb-1.5 inline-flex items-center gap-1.5 text-[12px] font-medium text-[var(--muted)] hover:text-[var(--ink)]">
            <Icon name="arrow-left" size={13} /> {site.name}
          </button>
          <div className="flex flex-wrap items-center gap-2.5">
            <h3 className="truncate font-display text-[20px] font-bold tracking-[-0.02em] text-[var(--ink)]">{camera.name}</h3>
            <span className="flex-none rounded-[5px] px-2 py-0.5 text-[10px] font-semibold tracking-[0.06em]" style={{ background: badge.bg, color: badge.color }}>
              {badge.label}
            </span>
          </div>
          <p className="mt-1 truncate font-mono-ui text-[11px] text-[#A9A398]">{camera.stream_identifier}</p>
        </div>
      </div>

      <div className="grid gap-3.5 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <section className="rounded-[12px] border border-[#E7E3DC] bg-[var(--card)] p-4">
          <LiveCameraPlayer
            cameraId={camera.id}
            cameraName={camera.name}
            organizationId={camera.organization_id}
            zonePolygons={zonePolygons}
            onRequestTicket={onRequestLiveTicket ?? (async () => null)}
          />
        </section>

        <div className="flex min-w-0 flex-col gap-3.5">
          <section className="overflow-hidden rounded-[12px] border border-[#E7E3DC] bg-[var(--card)]">
            <div className="border-b border-[#EDE9E1] px-[18px] py-3">
              <h4 className="font-display text-[14px] font-bold text-[var(--ink)]">Zonas desta câmera</h4>
            </div>
            {cameraZones.length === 0 ? (
              <p className="px-[18px] py-5 text-[13px] leading-6 text-[var(--muted)]">
                Nenhuma zona vinculada. Sem zona, a visão computacional avalia o quadro inteiro.
              </p>
            ) : (
              <ul>
                {cameraZones.map((zone) => {
                  const tone = zoneTypeBadge[zone.zone_type]
                  const drawn = polygonPointsOf(zone).length >= 3
                  return (
                    <li key={zone.id} className="flex items-center justify-between gap-3 border-b border-[#F0EDE6] px-[18px] py-2.5 last:border-b-0">
                      <div className="min-w-0">
                        <span className="rounded-full px-[7px] py-px text-[10px]" style={{ background: tone.bg, color: tone.color }}>{tone.label}</span>
                        <p className="mt-1 truncate font-mono-ui text-[11px] text-[#5F5951]">{zone.id}</p>
                      </div>
                      <span className={`flex-none text-[11px] ${drawn ? 'text-[#1F6B4A]' : 'text-[#946416]'}`}>
                        {drawn ? 'área desenhada' : 'quadro inteiro'}
                      </span>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>

          <section className="overflow-hidden rounded-[12px] border border-[#E7E3DC] bg-[var(--card)]">
            <div className="flex items-center justify-between gap-2 border-b border-[#EDE9E1] px-[18px] py-3">
              <h4 className="font-display text-[14px] font-bold text-[var(--ink)]">Incidentes desta câmera</h4>
              <button type="button" onClick={onOpenIncidents} className="text-[12px] font-medium text-[#B14A22] hover:underline">Ver todos</button>
            </div>
            {cameraIncidents.length === 0 ? (
              <p className="px-[18px] py-5 text-[13px] leading-6 text-[var(--muted)]">Nenhum incidente registrado por esta câmera.</p>
            ) : (
              <ul>
                {cameraIncidents.map((incident) => {
                  const tone = SEVERITY_TONE[incident.severity] ?? SEVERITY_TONE.low
                  return (
                    <li key={incident.id} className="flex items-center justify-between gap-3 border-b border-[#F0EDE6] px-[18px] py-2.5 last:border-b-0">
                      <div className="min-w-0">
                        <p className="truncate text-[13px] font-medium text-[var(--ink)]">{incident.summary}</p>
                        <p className="mt-0.5 font-mono-ui text-[10px] text-[#A9A398]">{incident.zone_id}</p>
                      </div>
                      <div className="flex flex-none items-center gap-2">
                        <span className="rounded-[5px] px-1.5 py-0.5 text-[10px] font-semibold uppercase" style={{ background: tone.bg, color: tone.color }}>{incident.severity}</span>
                        <span className="font-mono-ui text-[10px] text-[#A9A398]">{relativeTime(incident.created_at)}</span>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
