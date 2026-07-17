import { Modal } from '../../../../components/ui/dashboard'
import { ZoneForm } from '../forms/ZoneForm'
import type { OperationCamera, OperationSite, OperationZone } from '../../../../api/operations'
import type { ZoneFormValues } from '../schemas'

function polygonPointsOf(zone: OperationZone): [number, number][] {
  const points = (zone.polygon_json as { points?: [number, number][] } | undefined)?.points
  return Array.isArray(points) ? points : []
}

/** Cadastro/edição de zona. Ao editar, o polígono salvo volta para o editor. */
export function ZoneModal({
  open,
  sites,
  cameras,
  defaultSiteId,
  defaultCameraId,
  zone,
  onLoadCameraFrame,
  onClose,
  onSubmit,
}: {
  open: boolean
  sites: OperationSite[]
  cameras: OperationCamera[]
  defaultSiteId?: string
  defaultCameraId?: string
  /** Presente = edição. */
  zone?: OperationZone | null
  onLoadCameraFrame?: (cameraId: string) => Promise<string | null>
  onClose: () => void
  onSubmit: (values: ZoneFormValues) => Promise<void>
}) {
  const editando = Boolean(zone)
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editando ? 'Editar zona' : 'Cadastro de zona'}
      description={editando ? 'Ajuste o nome, o tipo ou redesenhe a área monitorada.' : 'Salva o cadastro na API real e atualiza a lista.'}
    >
      {open ? (
        <ZoneForm
          key={zone?.id ?? 'nova'}
          sites={sites}
          cameras={cameras}
          defaultSiteId={defaultSiteId}
          defaultCameraId={defaultCameraId}
          initial={
            zone
              ? {
                  site_id: zone.site_id,
                  camera_id: zone.camera_id,
                  name: zone.name ?? '',
                  zone_type: zone.zone_type,
                  status: zone.status,
                  polygon: polygonPointsOf(zone),
                }
              : undefined
          }
          submitLabel={editando ? 'Salvar zona' : 'Criar zona'}
          onLoadCameraFrame={onLoadCameraFrame}
          onSubmit={onSubmit}
          onCancel={onClose}
        />
      ) : null}
    </Modal>
  )
}
