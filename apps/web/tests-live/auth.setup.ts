import { expect, test as setup } from '@playwright/test'

const authFile = 'tests-live/.auth/live.json'

// Loga UMA vez e guarda a sessão: cada teste logando do zero estoura o rate limit da API
// (a suíte inteira falhava por 429, não por bug do produto).
setup('autentica uma vez e guarda a sessao', async ({ page }) => {
  await page.goto('/login')
  await page.getByRole('button', { name: 'Entrar com demo' }).click()
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 20000 })
  await page.context().storageState({ path: authFile })
})
