import { useParams } from '@tanstack/react-router'
import { Button } from '../../../components/ui/dashboard'
import { Icon } from '../../../components/ui/icons'
import { CameraDetailPage } from './CameraDetailPage'
import { useOperations } from './OperationsContext'

/** Rota `/dashboard/operations/sites/$siteId/cameras/$cameraId`. */
export function CameraRoute() {
  const { siteId, cameraId } = useParams({ strict: false }) as { siteId: string; cameraId: string }
  const {
    operationSites,
    operationCameras,
    operationZones,
    incidents,
    operationsLoading,
    operationsCatalog,
    ZONE_TYPE_BADGE,
    ENTITY_STATUS_BADGE,
    onOpenSite,
    onBackToSites,
    onRequestLiveTicket,
    onOpenIncidents,
  } = useOperations()

  if (operationsLoading && !operationsCatalog) {
    return <div className="rounded-xl border border-[#E7E3DC] bg-[var(--card)] px-4 py-8 text-sm text-[var(--muted)]">Carregando configuração operacional…</div>
  }

  const site = operationSites.find((item) => item.id === siteId) ?? null
  const camera = operationCameras.find((item) => item.id === cameraId) ?? null

  if (!site) {
    return (
      <div className="rounded-xl border border-dashed border-[color:var(--line)] bg-[var(--card)] px-5 py-8">
        <p className="font-display text-xl font-bold text-[var(--ink)]">Unidade não encontrada</p>
        <p className="mt-2 max-w-xl text-sm leading-7 text-[var(--muted)]">A unidade deste endereço não existe nesta organização ou foi removida.</p>
        <div className="mt-4">
          <Button size="sm" variant="secondary" onClick={onBackToSites}>
            <Icon name="arrow-left" size={15} /> Voltar para as unidades
          </Button>
        </div>
      </div>
    )
  }

  if (!camera) {
    return (
      <div className="rounded-xl border border-dashed border-[color:var(--line)] bg-[var(--card)] px-5 py-8">
        <p className="font-display text-xl font-bold text-[var(--ink)]">Câmera não encontrada</p>
        <p className="mt-2 max-w-xl text-sm leading-7 text-[var(--muted)]">A câmera deste endereço não existe nesta unidade ou foi removida.</p>
        <div className="mt-4">
          <Button size="sm" variant="secondary" onClick={() => onOpenSite(site.id)}>
            <Icon name="arrow-left" size={15} /> Voltar para {site.name}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <CameraDetailPage
      site={site}
      camera={camera}
      zones={operationZones}
      incidents={incidents}
      zoneTypeBadge={ZONE_TYPE_BADGE}
      statusBadge={ENTITY_STATUS_BADGE}
      onBack={() => onOpenSite(site.id)}
      onRequestLiveTicket={onRequestLiveTicket}
      onOpenIncidents={onOpenIncidents}
    />
  )
}
