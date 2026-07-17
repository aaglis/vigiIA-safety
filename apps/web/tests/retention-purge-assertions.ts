import { expect, type Page } from '@playwright/test'

export async function expectRetentionPurgeControls(page: Page) {
  await expect(page.getByRole('heading', { name: 'Retenção & LGPD' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Salvar retenção' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Executar purge' })).toBeVisible()
}
