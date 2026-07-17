import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Button, Modal, TextField } from '../../../../components/ui/dashboard'
import type { EdgeWorkerConfig } from '../../../../api/edgeWorkers'
import { workerConfigFormSchema, type WorkerConfigFormValues } from '../schemas'

/**
 * Checagem de configuração do worker. A `api_key` é usada só na chamada: nunca é
 * renderizada de volta, nem guardada — ao fechar, o estado vai junto.
 */
export function WorkerConfigModal({
  open,
  onClose,
  onCheck,
}: {
  open: boolean
  onClose: () => void
  onCheck: (payload: WorkerConfigFormValues) => Promise<EdgeWorkerConfig>
}) {
  const [resultado, setResultado] = useState<EdgeWorkerConfig | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<WorkerConfigFormValues>({
    resolver: zodResolver(workerConfigFormSchema),
    defaultValues: { client_id: '', api_key: '' },
    mode: 'onBlur',
  })

  const fechar = () => {
    setResultado(null)
    setErro(null)
    reset()
    onClose()
  }

  const submeter = async (values: WorkerConfigFormValues) => {
    setErro(null)
    setResultado(null)
    try {
      setResultado(await onCheck(values))
    } catch (error) {
      setErro(error instanceof Error ? error.message : 'Não foi possível checar a configuração.')
    } finally {
      // A chave não fica no formulário depois da checagem.
      reset({ client_id: values.client_id, api_key: '' })
    }
  }

  return (
    <Modal open={open} onClose={fechar} title="Checagem segura de configuração" description="A api_key é usada apenas na chamada e não é renderizada de volta.">
      <form className="space-y-5" onSubmit={handleSubmit(submeter)} noValidate>
        <TextField label="client_id" placeholder="edge-client-123" helperText="Informe o client_id do worker." errorText={errors.client_id?.message} {...register('client_id')} />
        <TextField label="api_key" type="password" placeholder="••••••••" helperText="Usada só na checagem; não é persistida." errorText={errors.api_key?.message} {...register('api_key')} />

        <div className="rounded-[12px] border border-[#E3D8C8] bg-[#F7F0E2] px-4 py-3 text-sm leading-6 text-[#5a4a2a]">
          Nunca cole a chave em chat, logs ou tickets. Se funcionar, a tela mostra apenas metadados seguros.
        </div>

        {erro ? <div className="rounded-[12px] border border-[rgba(193,85,43,0.2)] bg-[rgba(193,85,43,0.08)] px-4 py-3 text-sm text-[#9e4120]">{erro}</div> : null}

        {resultado ? (
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[14px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-3.5">
              <p className="font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">WORKER</p>
              <p className="mt-2 truncate text-sm font-semibold text-[var(--ink)]">{resultado.worker.name}</p>
              <p className="mt-1 truncate text-xs text-[var(--muted-2)]">{resultado.worker.id}</p>
            </div>
            <div className="rounded-[14px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-3.5">
              <p className="font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">CLIENT ID</p>
              <p className="mt-2 truncate text-sm font-semibold text-[var(--ink)]">{resultado.worker.client_id}</p>
              <p className="mt-1 text-xs text-[var(--muted-2)]">api_key omitida.</p>
            </div>
            <div className="rounded-[14px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-3.5">
              <p className="font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">ESCOPO</p>
              <p className="mt-2 text-sm font-semibold text-[var(--ink)]">{resultado.allowed_camera_ids.length} câmeras</p>
              <p className="mt-1 text-xs text-[var(--muted-2)]">capabilities: {resultado.capabilities.join(' · ')}</p>
            </div>
          </div>
        ) : null}

        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-end gap-2.5">
            <Button type="button" variant="secondary" onClick={fechar}>Fechar</Button>
            <Button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Checando…' : 'Checar'}</Button>
          </div>
          <p className="text-right text-[12px] leading-5 text-[var(--label)]">Ao concluir, a chave é limpa da tela e nunca reexibida.</p>
        </div>
      </form>
    </Modal>
  )
}
