import { expect, type Page } from '@playwright/test'

export async function expectDemoModeNotActive(page: Page) {
  await expect(page.getByText('Modo demonstração local')).toHaveCount(0)
}
