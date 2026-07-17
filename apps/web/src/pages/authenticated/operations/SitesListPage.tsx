import { Button } from '../../../components/ui/dashboard'
import { Icon } from '../../../components/ui/icons'
import type { OperationCamera, OperationSafetyRule, OperationSite, OperationZone } from '../../../api/operations'

/** Nível raiz de Operações: só os sites. Câmeras/zonas/regras vivem na página do site. */
export function SitesListPage({
  sites,
  cameras,
  zones,
  rules,
  statusBadge,
  onOpenSite,
  onNewSite,
}: {
  sites: OperationSite[]
  cameras: OperationCamera[]
  zones: OperationZone[]
  rules: OperationSafetyRule[]
  statusBadge: Record<string, { label: string; bg: string; color: string }>
  onOpenSite: (siteId: string) => void
  onNewSite: () => void
}) {
  if (sites.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[color:var(--line)] bg-[var(--card)] px-5 py-8">
        <p className="font-display text-xl font-bold text-[var(--ink)]">Nenhuma unidade configurada</p>
        <p className="mt-2 max-w-xl text-sm leading-7 text-[var(--muted)]">Para preparar o piloto: cadastre uma unidade → conecte ao menos uma câmera → desenhe as zonas → associe regras e EPIs.</p>
        <div className="mt-4">
          <Button size="sm" onClick={onNewSite}>
            <Icon name="plus" size={15} /> Cadastrar primeira unidade
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between px-1">
        <span className="font-mono-ui text-[10px] tracking-[0.14em] text-[#A9A398]">UNIDADES · {sites.length}</span>
        <button type="button" onClick={onNewSite} className="text-[12px] font-medium text-[#B14A22] hover:underline">+ Nova unidade</button>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {sites.map((site) => {
          const badge = statusBadge[site.status]
          const siteCameras = cameras.filter((camera) => camera.site_id === site.id)
          const siteZones = zones.filter((zone) => zone.site_id === site.id)
          const siteRules = rules.filter((rule) => rule.site_id === site.id || (rule.zone_id ? siteZones.some((zone) => zone.id === rule.zone_id) : false))
          const offline = siteCameras.filter((camera) => camera.status !== 'active').length
          return (
            <button
              key={site.id}
              type="button"
              onClick={() => onOpenSite(site.id)}
              data-testid={`site-card-${site.id}`}
              className={`group rounded-[11px] border border-[#E7E3DC] bg-[var(--card)] px-4 py-4 text-left transition hover:border-[#EAD8CD] hover:bg-[#FCF7F3] ${site.status !== 'active' ? 'opacity-80' : ''}`}
            >
              <span className="mb-1.5 flex items-center justify-between gap-2">
                <span className="truncate text-sm font-semibold text-[var(--ink)]">{site.name}</span>
                <span className="flex-none rounded-[5px] px-2 py-0.5 text-[10px] font-semibold tracking-[0.06em]" style={{ background: badge.bg, color: badge.color }}>
                  {badge.label}
                </span>
              </span>
              {site.address ? <p className="mb-2.5 truncate text-xs text-[#8E887B]">{site.address}</p> : <p className="mb-2.5 text-xs text-[#A9A398]">Sem endereço</p>}
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono-ui text-[11px] text-[#5F5951]">
                  {siteCameras.length} câm · {siteZones.length} zonas · {siteRules.length} regras
                </span>
                <span className="flex-none text-[#C0BAB0] transition group-hover:translate-x-0.5 group-hover:text-[var(--accent)]">
                  <Icon name="chevron-right" size={14} />
                </span>
              </div>
              {offline > 0 ? (
                <p className="mt-2 flex items-center gap-1.5 text-[11px] text-[#946416]">
                  <Icon name="alert-triangle" size={11} /> {offline} câmera(s) fora de operação
                </p>
              ) : null}
            </button>
          )
        })}
      </div>
    </div>
  )
}
