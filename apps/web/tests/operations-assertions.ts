import { expect, type Page } from '@playwright/test'

export async function expectOperationalSiteVisible(page: Page, siteName: string) {
  await expect(page.getByText(siteName, { exact: true })).toBeVisible()
}
