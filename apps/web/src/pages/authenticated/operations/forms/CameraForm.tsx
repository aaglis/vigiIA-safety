import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Button, SelectField, TextField } from '../../../../components/ui/dashboard'
import type { OperationSite } from '../../../../api/operations'
import { cameraEditFormSchema, cameraFormSchema, type CameraFormValues } from '../schemas'

export function CameraForm({
  sites,
  defaultSiteId,
  initial,
  submitLabel = 'Criar câmera',
  requireStream = true,
  onSubmit,
  onCancel,
}: {
  sites: OperationSite[]
  defaultSiteId?: string
  initial?: Partial<CameraFormValues>
  submitLabel?: string
  requireStream?: boolean
  onSubmit: (values: CameraFormValues) => Promise<void>
  onCancel: () => void
}) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CameraFormValues>({
    resolver: zodResolver(requireStream ? cameraFormSchema : cameraEditFormSchema),
    defaultValues: {
      site_id: initial?.site_id ?? defaultSiteId ?? sites[0]?.id ?? '',
      name: initial?.name ?? '',
      stream_identifier: initial?.stream_identifier ?? '',
      status: initial?.status ?? 'active',
    },
    mode: 'onBlur',
  })

  return (
    <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
      <SelectField label="Unidade" helperText="A câmera será vinculada à unidade escolhida." errorText={errors.site_id?.message} {...register('site_id')}>
        <option value="">Selecione uma unidade</option>
        {sites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
      </SelectField>
      <TextField
        label="Nome da câmera"
        placeholder="Ex.: Câmera 07"
        helperText="Nome curto para reconhecimento rápido."
        errorText={errors.name?.message}
        {...register('name')}
      />
      <TextField
        label="URL do stream"
        placeholder={requireStream ? 'rtsp://10.0.0.20:554/live' : 'deixe em branco para manter a URL atual'}
        helperText={requireStream ? 'Endereço RTSP/RTMP da câmera. A visão computacional roda direto neste stream.' : 'Por segurança a URL salva não é exibida. Preencha só se for trocar o stream.'}
        errorText={errors.stream_identifier?.message}
        {...register('stream_identifier')}
      />
      <SelectField label="Status" helperText="Estado de publicação da câmera." errorText={errors.status?.message} {...register('status')}>
        <option value="active">Ativo</option>
        <option value="inactive">Inativo</option>
        <option value="suspended">Suspenso</option>
      </SelectField>
      <div className="flex flex-wrap items-center justify-end gap-2.5">
        <Button type="button" variant="secondary" onClick={onCancel}>Cancelar</Button>
        <Button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Salvando…' : submitLabel}</Button>
      </div>
    </form>
  )
}
