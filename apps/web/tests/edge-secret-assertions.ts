import { expect, type Page } from '@playwright/test'

export async function expectEdgeSecretNotRendered(page: Page, secret: string) {
  await expect(page.getByText(secret, { exact: true })).toHaveCount(0)
}
