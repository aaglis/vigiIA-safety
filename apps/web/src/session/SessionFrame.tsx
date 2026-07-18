import type { ReactNode } from 'react'
import type { Screen } from '../navigation/routes'
import { LandingPage } from '../pages/public/LandingPage'
import { LoginPage } from '../pages/public/LoginPage'

type SessionFrameProps = {
  screen: Screen
  children: ReactNode
  booting: boolean
  loginEmail: string
  loginPassword: string
  loginLoading: boolean
  loginError: string | null
  onLandingLogin: () => void
  onScrollToSection: (id: string) => void
  onLoginBack: () => void
  onEmailChange: (value: string) => void
  onPasswordChange: (value: string) => void
  onLoginSubmit: () => void
  onDemoLogin: () => void
  onLocalDemo: () => void
}

export function SessionFrame({
  screen,
  children,
  booting,
  loginEmail,
  loginPassword,
  loginLoading,
  loginError,
  onLandingLogin,
  onScrollToSection,
  onLoginBack,
  onEmailChange,
  onPasswordChange,
  onLoginSubmit,
  onDemoLogin,
  onLocalDemo,
}: SessionFrameProps) {
  return (
    <main className="relative min-h-screen bg-[var(--bg)] text-[var(--ink)]">
      {screen === 'landing' && <LandingPage onLogin={onLandingLogin} onScrollToSection={onScrollToSection} />}
      {screen === 'login' && (
        <LoginPage
          email={loginEmail}
          password={loginPassword}
          loading={loginLoading}
          error={loginError}
          onBack={onLoginBack}
          onEmailChange={onEmailChange}
          onPasswordChange={onPasswordChange}
          onSubmit={onLoginSubmit}
          onDemoLogin={onDemoLogin}
          onLocalDemo={onLocalDemo}
        />
      )}
      {children}
      {booting ? <div className="pointer-events-none fixed bottom-4 right-4 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-4 py-2 text-xs uppercase tracking-[0.24em] text-[var(--muted)] shadow-[0_12px_30px_rgba(32,27,24,0.1)]">Verificando sessão…</div> : null}
    </main>
  )
}
