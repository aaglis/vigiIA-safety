import { Modal } from '../../../../components/ui/dashboard'
import { SiteForm } from '../forms/SiteForm'
import type { OperationSite } from '../../../../api/operations'
import type { SiteFormValues } from '../schemas'

/** Cadastro/edição de unidade. Um modal por ação: quem clica em "Nova unidade" não
 *  deveria poder trocar o tipo do cadastro por dentro do próprio modal. */
export function SiteModal({
  open,
  site,
  onClose,
  onSubmit,
}: {
  open: boolean
  /** Presente = edição. */
  site?: OperationSite | null
  onClose: () => void
  onSubmit: (values: SiteFormValues) => Promise<void>
}) {
  const editando = Boolean(site)
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editando ? 'Editar unidade' : 'Cadastro de unidade'}
      description={editando ? 'Altera o cadastro na API real e atualiza a lista.' : 'Salva o cadastro na API real e atualiza a lista.'}
    >
      {open ? (
        <SiteForm
          // key força o form a remontar com os valores da unidade aberta: sem isso o
          // react-hook-form mantém os defaultValues da primeira montagem.
          key={site?.id ?? 'novo'}
          initial={site ? { name: site.name, address: site.address ?? '', status: site.status } : undefined}
          submitLabel={editando ? 'Salvar unidade' : 'Criar unidade'}
          onSubmit={onSubmit}
          onCancel={onClose}
        />
      ) : null}
    </Modal>
  )
}
