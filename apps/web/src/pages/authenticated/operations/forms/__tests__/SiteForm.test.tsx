import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SiteForm } from '../SiteForm'

describe('SiteForm', () => {
  it('renders defaults and submits valid values', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn().mockResolvedValue(undefined)

    render(<SiteForm initial={{ name: 'Base Norte', address: 'Rua 1', status: 'inactive' }} onSubmit={onSubmit} onCancel={vi.fn()} />)

    expect(screen.getByRole('textbox', { name: /nome da unidade/i })).toHaveValue('Base Norte')
    expect(screen.getByRole('textbox', { name: /endereço \/ referência/i })).toHaveValue('Rua 1')
    expect(screen.getByRole('combobox', { name: /status/i })).toHaveValue('inactive')

    await user.clear(screen.getByRole('textbox', { name: /nome da unidade/i }))
    await user.type(screen.getByRole('textbox', { name: /nome da unidade/i }), 'Pátio Sul')
    await user.click(screen.getByRole('button', { name: 'Criar unidade' }))

    expect(onSubmit).toHaveBeenCalledWith({ name: 'Pátio Sul', address: 'Rua 1', status: 'inactive' }, expect.anything())
  })

  it('blocks invalid submit with field message', async () => {
    const user = userEvent.setup()
    render(<SiteForm onSubmit={vi.fn()} onCancel={vi.fn()} />)

    await user.click(screen.getByRole('button', { name: 'Criar unidade' }))

    expect(await screen.findByText('Informe o nome da unidade (mínimo 2 caracteres).')).toBeVisible()
  })
})
