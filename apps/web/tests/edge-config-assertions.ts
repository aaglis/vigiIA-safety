import { expect, type Locator } from '@playwright/test'

export async function expectEdgeConfigRedacted(dialog: Locator, clientId: string) {
  await expect(dialog.getByText(clientId, { exact: true })).toBeVisible()
  await expect(dialog.getByText('api_key omitida.', { exact: true })).toBeVisible()
}
