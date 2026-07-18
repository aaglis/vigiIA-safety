import { Modal } from '../../../../components/ui/dashboard'
import { CameraForm } from '../forms/CameraForm'
import type { OperationCamera, OperationSite, OperationZone } from '../../../../api/operations'
import type { CameraFormValues } from '../schemas'

/** Cadastro/edição de câmera. */
export function CameraModal({
  open,
  sites,
  zones,
  defaultSiteId,
  camera,
  onClose,
  onSubmit,
}: {
  open: boolean
  sites: OperationSite[]
  zones: OperationZone[]
  defaultSiteId?: string
  /** Presente = edição. */
  camera?: OperationCamera | null
  onClose: () => void
  onSubmit: (values: CameraFormValues) => Promise<void>
}) {
  const editando = Boolean(camera)
  // Zonas foram desenhadas sobre o frame DESTA câmera. Trocar o stream troca a imagem,
  // e o polígono continua nas mesmas coordenadas — passa a marcar outro lugar.
  const zonasDesenhadas = camera
    ? zones.filter((zone) => zone.camera_id === camera.id && ((zone.polygon_json as { points?: unknown[] } | undefined)?.points?.length ?? 0) >= 3)
    : []
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editando ? 'Editar câmera' : 'Cadastro de câmera'}
      description={editando ? 'Altera o cadastro na API real e atualiza a lista.' : 'Salva o cadastro na API real e atualiza a lista.'}
    >
      {open && zonasDesenhadas.length > 0 ? (
        <div className="mb-5 rounded-[10px] border border-[#E3D8C8] bg-[#F7F0E2] px-3.5 py-2.5">
          <p className="text-[12px] leading-5 text-[#5a4a2a]">
            <span className="font-semibold">
              {zonasDesenhadas.length === 1 ? 'Há 1 zona desenhada' : `Há ${zonasDesenhadas.length} zonas desenhadas`} sobre a imagem desta câmera.
            </span>{' '}
            Trocar a URL do stream muda a imagem, mas o desenho continua nas mesmas coordenadas — as áreas podem passar a
            marcar outro lugar. Confira {zonasDesenhadas.length === 1 ? 'a zona' : 'as zonas'} depois de salvar:{' '}
            {zonasDesenhadas.map((zone) => zone.name || zone.id).join(', ')}.
          </p>
        </div>
      ) : null}

      {open ? (
        <CameraForm
          key={camera?.id ?? 'nova'}
          sites={sites}
          defaultSiteId={defaultSiteId}
          initial={camera ? { site_id: camera.site_id, name: camera.name, stream_identifier: '', status: camera.status } : undefined}
          submitLabel={editando ? 'Salvar câmera' : 'Criar câmera'}
          requireStream={!editando}
          onSubmit={onSubmit}
          onCancel={onClose}
        />
      ) : null}
    </Modal>
  )
}
