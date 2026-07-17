import { expect, type Page } from '@playwright/test'

export async function expectSignedEvidenceUrlNotRendered(page: Page, signedUrl: string) {
  await expect(page.locator(`a[href="${signedUrl}"]`)).toHaveCount(0)
  await expect(page.getByText(signedUrl)).toHaveCount(0)
  await expect(page.getByText('X-Amz-Signature')).toHaveCount(0)
}
