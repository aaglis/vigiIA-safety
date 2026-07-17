import { useEffect, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { Button, SelectField, TextField } from '../../../../components/ui/dashboard'
import { ZonePolygonEditor } from '../../../../components/operations/ZonePolygonEditor'
import type { OperationCamera, OperationSite } from '../../../../api/operations'
import { zoneFormSchema, type ZoneFormValues } from '../schemas'

export function ZoneForm({
  sites,
  cameras,
  defaultSiteId,
  defaultCameraId,
  initial,
  submitLabel = 'Criar zona',
  onLoadCameraFrame,
  onSubmit,
  onCancel,
}: {
  sites: OperationSite[]
  cameras: OperationCamera[]
  defaultSiteId?: string
  defaultCameraId?: string
  initial?: Partial<ZoneFormValues>
  submitLabel?: string
  onLoadCameraFrame?: (cameraId: string) => Promise<string | null>
  onSubmit: (values: ZoneFormValues) => Promise<void>
  onCancel: () => void
}) {
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<ZoneFormValues>({
    resolver: zodResolver(zoneFormSchema),
    defaultValues: {
      site_id: initial?.site_id ?? defaultSiteId ?? sites[0]?.id ?? '',
      camera_id: initial?.camera_id ?? defaultCameraId ?? cameras[0]?.id ?? '',
      name: initial?.name ?? '',
      zone_type: initial?.zone_type ?? 'restricted',
      status: initial?.status ?? 'active',
      // Ao editar, o desenho salvo volta para o editor — senão o usuário teria de
      // redesenhar do zero só para mudar o nome.
      polygon: initial?.polygon ?? [],
    },
    mode: 'onBlur',
  })

  const cameraId = useWatch({ control, name: 'camera_id' })
  const zoneType = useWatch({ control, name: 'zone_type' })
  const [frameUrl, setFrameUrl] = useState<string | null>(null)
  const [frameLoading, setFrameLoading] = useState(false)

  // Fundo do editor: frame da câmera escolhida (ao vivo, com evidência como fallback).
  useEffect(() => {
    if (!cameraId || !onLoadCameraFrame) {
      setFrameUrl(null)
      return
    }
    let active = true
    setFrameLoading(true)
    setFrameUrl(null)
    void onLoadCameraFrame(cameraId)
      .then((url) => {
        if (active) setFrameUrl(url)
      })
      .finally(() => {
        if (active) setFrameLoading(false)
      })
    return () => {
      active = false
    }
  }, [cameraId, onLoadCameraFrame])

  const siteById = new Map(sites.map((site) => [site.id, site] as const))

  return (
    <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
      <SelectField label="Unidade" helperText="Escolha a unidade que contém a zona." errorText={errors.site_id?.message} {...register('site_id')}>
        <option value="">Selecione uma unidade</option>
        {sites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
      </SelectField>
      <SelectField label="Câmera" helperText="A zona precisa estar ancorada em uma câmera." errorText={errors.camera_id?.message} {...register('camera_id')}>
        <option value="">Selecione uma câmera</option>
        {cameras.map((camera) => (
          <option key={camera.id} value={camera.id}>{camera.name} · {siteById.get(camera.site_id)?.name ?? camera.site_id}</option>
        ))}
      </SelectField>
      <TextField
        label="Nome da área"
        placeholder="Ex.: Porta da Doca"
        helperText="Como essa área é chamada na planta. É o que aparece no alerta."
        errorText={errors.name?.message}
        {...register('name')}
      />
      <SelectField label="Tipo" helperText="Categoria operacional da zona." errorText={errors.zone_type?.message} {...register('zone_type')}>
        <option value="access">Acesso</option>
        <option value="restricted">Restrita</option>
        <option value="ppe">EPI</option>
      </SelectField>

      {/* O polígono é estado composto (não cabe em `register`): Controller liga o editor
          ao formulário e mantém a validação (>= 3 pontos) no mesmo schema. */}
      <Controller
        control={control}
        name="polygon"
        render={({ field }) => (
          <div className="space-y-1.5">
            <div className="rounded-[10px] border border-[#E3D8C8] bg-[#F7F0E2] px-3.5 py-2.5">
              <p className="text-[12px] leading-5 text-[#5a4a2a]">
                <span className="font-semibold">Marque a área do chão</span>, não a parede ou o objeto. A detecção olha
                onde os pés da pessoa tocam o piso — desenhar sobre uma porta ao fundo não impede que alguém passe na
                frente dela.
              </p>
            </div>
            <ZonePolygonEditor
              frameUrl={frameUrl}
              frameLoading={frameLoading}
              points={field.value}
              onChange={field.onChange}
              zoneType={zoneType}
            />
            {errors.polygon?.message ? <p className="text-[12px] leading-5 text-[#9e4120]">{errors.polygon.message}</p> : null}
          </div>
        )}
      />

      <SelectField label="Status" helperText="Estado de publicação da zona." errorText={errors.status?.message} {...register('status')}>
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
