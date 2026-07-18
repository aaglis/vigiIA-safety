import { useEffect, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { Button, Modal, SelectField, TextField } from '../../../../components/ui/dashboard'
import { Icon } from '../../../../components/ui/icons'
import type { RegisterEdgeWorkerResponse } from '../../../../api/edgeWorkers'
import type { OperationCamera, OperationSite } from '../../../../api/operations'
import { edgeWorkerFormSchema, type EdgeWorkerFormValues } from '../schemas'

/**
 * Registro de edge worker. A chave nasce aqui e é exibida UMA vez — não há endpoint que
 * a recupere depois. Por isso o resultado troca o formulário por uma tela de cópia, e
 * fechar descarta tudo.
 */
export function EdgeWorkerModal({
  open,
  sites,
  cameras,
  defaultSiteId,
  onClose,
  onRegister,
  onRegistered,
}: {
  open: boolean
  sites: OperationSite[]
  cameras: OperationCamera[]
  defaultSiteId?: string
  onClose: () => void
  onRegister: (payload: EdgeWorkerFormValues) => Promise<RegisterEdgeWorkerResponse>
  onRegistered: (resposta: RegisterEdgeWorkerResponse) => void
}) {
  const [resultado, setResultado] = useState<RegisterEdgeWorkerResponse | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [copiado, setCopiado] = useState(false)

  const {
    register,
    handleSubmit,
    control,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<EdgeWorkerFormValues>({
    resolver: zodResolver(edgeWorkerFormSchema),
    defaultValues: { site_id: defaultSiteId ?? sites[0]?.id ?? '', name: '', allowed_camera_ids: [] },
    mode: 'onBlur',
  })

  const siteId = useWatch({ control, name: 'site_id' })
  const siteCameras = cameras.filter((camera) => camera.site_id === siteId)
  const site = sites.find((item) => item.id === siteId) ?? null

  // Trocar de unidade deve reescopar as câmeras: manter a seleção antiga daria à
  // credencial acesso a câmeras de outro site.
  useEffect(() => {
    if (!open) return
    setValue('allowed_camera_ids', siteCameras.map((camera) => camera.id))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, siteId, cameras])

  const fechar = () => {
    setResultado(null)
    setErro(null)
    setCopiado(false)
    reset({ site_id: defaultSiteId ?? sites[0]?.id ?? '', name: '', allowed_camera_ids: [] })
    onClose()
  }

  const copiarChave = async () => {
    if (!resultado) return
    try {
      await navigator.clipboard.writeText(resultado.api_key)
      setCopiado(true)
    } catch {
      setCopiado(false)
    }
  }

  const submeter = async (values: EdgeWorkerFormValues) => {
    setErro(null)
    try {
      const resposta = await onRegister(values)
      setResultado(resposta)
      onRegistered(resposta)
    } catch (error) {
      setErro(error instanceof Error ? error.message : 'Não foi possível registrar o worker.')
    }
  }

  return (
    <Modal
      open={open}
      onClose={fechar}
      title="Registro seguro de edge worker"
      description="A chave é exibida uma única vez. Copie agora e guarde em um secret manager ou variável de ambiente."
    >
      {resultado ? (
        <div className="space-y-5">
          <div className="rounded-[12px] border border-[#E3D8C8] bg-[#F7F0E2] px-4 py-3 text-sm leading-6 text-[#5a4a2a]">
            <span className="font-semibold text-[#3f3212]">Chave gerada com sucesso.</span> Não será possível recuperá-la depois que você fechar este painel. Não cole em chat, logs ou tickets públicos.
          </div>

          <div className="rounded-[16px] border border-[rgba(32,27,24,0.9)] bg-[rgba(32,27,24,0.96)] px-4 py-4 text-[var(--paper)] shadow-[0_16px_38px_rgba(32,27,24,0.2)]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-mono-ui text-[10px] tracking-[0.16em] text-[#b7afa5]">API KEY · VISUALIZAÇÃO ÚNICA</p>
                <p className="mt-1 text-sm text-[#d7cec4]">Copie agora e mova para o secret manager do worker.</p>
              </div>
              <Button variant="secondary" size="sm" onClick={copiarChave} className="border-transparent bg-[rgba(255,255,255,0.08)] text-[var(--paper)] hover:bg-[rgba(255,255,255,0.14)]">
                <Icon name="copy" size={14} /> {copiado ? 'Copiada' : 'Copiar chave'}
              </Button>
            </div>
            <code className="mt-4 block break-all rounded-[12px] border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.04)] px-3.5 py-3 font-mono-ui text-[13px] leading-6 text-[#f5f3ef]">{resultado.api_key}</code>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[14px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-3.5">
              <p className="font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">WORKER</p>
              <p className="mt-2 truncate text-sm font-semibold text-[var(--ink)]">{resultado.worker.name}</p>
              <p className="mt-1 truncate text-xs text-[var(--muted-2)]">{resultado.worker.id}</p>
            </div>
            <div className="rounded-[14px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-3.5">
              <p className="font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">CLIENT ID</p>
              <p className="mt-2 truncate text-sm font-semibold text-[var(--ink)]">{resultado.worker.client_id}</p>
              <p className="mt-1 text-xs text-[var(--muted-2)]">Use este valor nas chamadas X-Edge-Client-Id.</p>
            </div>
            <div className="rounded-[14px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-3.5">
              <p className="font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">CÂMERAS</p>
              <p className="mt-2 text-sm font-semibold text-[var(--ink)]">{resultado.worker.allowed_camera_ids.length} liberadas</p>
              <p className="mt-1 text-xs text-[var(--muted-2)]">Escopo mínimo para o edge worker.</p>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-end gap-2.5">
              <Button variant="secondary" onClick={copiarChave}>Copiar chave</Button>
              <Button onClick={fechar}>Fechar</Button>
            </div>
            <p className="text-right text-[12px] leading-5 text-[var(--label)]">A chave some ao fechar. Guarde em secret manager e nunca em texto aberto.</p>
          </div>
        </div>
      ) : (
        <form className="space-y-5" onSubmit={handleSubmit(submeter)} noValidate>
          <SelectField label="Unidade" helperText="A credencial nasce ligada à unidade escolhida." errorText={errors.site_id?.message} {...register('site_id')}>
            <option value="">Selecione uma unidade</option>
            {sites.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </SelectField>

          <TextField label="Nome do worker" placeholder="Ex.: Gateway Pátio Sul" helperText="Nome humano para identificar a credencial nas operações." errorText={errors.name?.message} {...register('name')} />

          <Controller
            control={control}
            name="allowed_camera_ids"
            render={({ field }) => (
              <div className="rounded-[16px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-display text-[17px] font-bold text-[var(--ink)]">Câmeras permitidas</p>
                    <p className="mt-1 text-sm leading-6 text-[var(--muted)]">Selecione só as câmeras que esse worker pode consumir. O escopo vai junto da chave.</p>
                  </div>
                  <span className="rounded-[5px] bg-[#F3E9D6] px-2 py-0.5 text-[10px] font-semibold tracking-[0.06em] text-[#946416]">SENSÍVEL</span>
                </div>
                {siteCameras.length > 0 ? (
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    {siteCameras.map((camera) => {
                      const marcada = field.value.includes(camera.id)
                      return (
                        <label key={camera.id} className={`flex items-center gap-3 rounded-[12px] border px-3 py-3 text-sm transition ${marcada ? 'border-[rgba(193,85,43,0.28)] bg-[rgba(193,85,43,0.05)]' : 'border-[color:var(--line)] bg-[var(--paper)] hover:bg-white'}`}>
                          <input
                            type="checkbox"
                            checked={marcada}
                            onChange={(event) =>
                              field.onChange(event.target.checked ? Array.from(new Set([...field.value, camera.id])) : field.value.filter((id) => id !== camera.id))
                            }
                            className="h-4 w-4 rounded border-[color:var(--line)] text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(193,85,43,0.16)]"
                          />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate font-medium text-[var(--ink)]">{camera.name}</span>
                            <span className="block truncate text-xs text-[var(--muted-2)]">{site?.name ?? camera.site_id} · {camera.display_stream_identifier ?? 'Fonte configurada'}</span>
                          </span>
                        </label>
                      )
                    })}
                  </div>
                ) : (
                  <p className="mt-4 rounded-[12px] border border-dashed border-[color:var(--line)] px-4 py-4 text-sm text-[var(--muted)]">Essa unidade ainda não tem câmeras. Cadastre uma câmera antes de registrar o worker.</p>
                )}
                {errors.allowed_camera_ids?.message ? <p className="mt-3 text-[12px] leading-5 text-[#9e4120]">{errors.allowed_camera_ids.message}</p> : null}
              </div>
            )}
          />

          {erro ? <div className="rounded-[12px] border border-[rgba(193,85,43,0.2)] bg-[rgba(193,85,43,0.08)] px-4 py-3 text-sm text-[#9e4120]">{erro}</div> : null}

          <div className="rounded-[12px] border border-[#E3D8C8] bg-[#F7F0E2] px-4 py-3 text-sm leading-6 text-[#5a4a2a]">
            <span className="font-semibold text-[#3f3212]">Chave sensível:</span> copie uma vez, guarde em secret manager e não compartilhe em chat, log ou print.
          </div>

          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-end gap-2.5">
              <Button type="button" variant="secondary" onClick={fechar}>Cancelar</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Registrando…' : 'Registrar credencial'}</Button>
            </div>
            <p className="text-right text-[12px] leading-5 text-[var(--label)]">A chave aparece uma única vez, logo após o registro.</p>
          </div>
        </form>
      )}
    </Modal>
  )
}
