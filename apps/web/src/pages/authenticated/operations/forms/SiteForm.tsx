import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Button, SelectField, TextField } from '../../../../components/ui/dashboard'
import { siteFormSchema, type SiteFormValues } from '../schemas'

export function SiteForm({ onSubmit, onCancel }: { onSubmit: (values: SiteFormValues) => Promise<void>; onCancel: () => void }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SiteFormValues>({
    resolver: zodResolver(siteFormSchema),
    defaultValues: { name: '', address: '', status: 'active' },
    mode: 'onBlur',
  })

  return (
    <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
      <TextField
        label="Nome da unidade"
        placeholder="Ex.: Pátio Sul"
        helperText="Identificação visível para operadores e auditoria."
        errorText={errors.name?.message}
        {...register('name')}
      />
      <TextField
        label="Endereço / referência"
        placeholder="Ex.: Portaria 2 · área externa"
        helperText="Ajuda a localizar a unidade."
        errorText={errors.address?.message}
        {...register('address')}
      />
      <SelectField label="Status" helperText="Estado de publicação do cadastro." errorText={errors.status?.message} {...register('status')}>
        <option value="active">Ativo</option>
        <option value="inactive">Inativo</option>
        <option value="suspended">Suspenso</option>
      </SelectField>
      <div className="flex flex-wrap items-center justify-end gap-2.5">
        <Button type="button" variant="secondary" onClick={onCancel}>Cancelar</Button>
        <Button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Salvando…' : 'Criar unidade'}</Button>
      </div>
    </form>
  )
}
