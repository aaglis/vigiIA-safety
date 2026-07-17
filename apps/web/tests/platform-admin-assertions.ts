import { expect, type Page } from '@playwright/test'

export async function expectPlatformAdminControls(page: Page) {
  await expect(page.getByText('Plataforma Alpha', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Nova organização' })).toBeVisible()
}
