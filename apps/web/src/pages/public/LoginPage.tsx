import { MonogramMark } from '../../components/ui/brand'

export function LoginPage({
  email,
  password,
  loading,
  error,
  onBack,
  onEmailChange,
  onPasswordChange,
  onSubmit,
  onDemoLogin,
  onLocalDemo,
}: {
  email: string
  password: string
  loading: boolean
  error: string | null
  onBack: () => void
  onEmailChange: (value: string) => void
  onPasswordChange: (value: string) => void
  onSubmit: () => void
  onDemoLogin: () => void
  onLocalDemo: () => void
}) {
  return (
    <div className="relative mx-auto flex min-h-screen w-full max-w-5xl flex-col px-5 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between py-6">
        <button type="button" onClick={onBack} className="text-sm font-medium text-[var(--muted)] transition hover:text-[var(--ink)]">
          ← Voltar à página inicial
        </button>
      </div>

      <div className="flex flex-1 items-center justify-center pb-20">
        <div className="reveal w-full max-w-[360px]">
          <button type="button" onClick={onBack} className="mx-auto mb-9 flex flex-col items-center gap-3">
            <MonogramMark className="h-11 w-11" />
            <span className="flex flex-col items-center leading-none">
              <span className="text-lg font-semibold tracking-[0.03em] text-[var(--ink)]">VIGIA</span>
              <span className="mt-1 font-mono-ui text-[8px] uppercase tracking-[0.34em] text-[var(--label)]">SAFETY</span>
            </span>
          </button>

          <h1 className="text-center font-display text-3xl font-bold tracking-[-0.02em] text-[var(--ink)]">Entrar</h1>
          <p className="mt-1.5 text-center text-sm text-[var(--muted)]">Acesso à plataforma de segurança operacional.</p>

          <form className="mt-8 space-y-4" onSubmit={(event) => { event.preventDefault(); onSubmit() }}>
            <div>
              <label htmlFor="login-email" className="mb-1.5 block text-[13px] font-medium text-[#403933]">E-mail</label>
              <input id="login-email" type="email" value={email} onChange={(event) => onEmailChange(event.target.value)} className="h-12 w-full rounded-[10px] border border-[#dcd7cc] bg-[var(--card)] px-3.5 text-[15px] text-[var(--ink)] outline-none transition placeholder:text-[#a09a8e] focus:border-[var(--accent)] focus:ring-2 focus:ring-[rgba(193,85,43,0.16)]" placeholder="voce@empresa.com" />
            </div>
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label htmlFor="login-password" className="text-[13px] font-medium text-[#403933]">Senha</label>
                <button type="button" className="text-[13px] text-[var(--accent)] transition hover:opacity-80">Esqueci minha senha</button>
              </div>
              <input id="login-password" type="password" value={password} onChange={(event) => onPasswordChange(event.target.value)} className="h-12 w-full rounded-[10px] border border-[#dcd7cc] bg-[var(--card)] px-3.5 text-[15px] text-[var(--ink)] outline-none transition placeholder:text-[#a09a8e] focus:border-[var(--accent)] focus:ring-2 focus:ring-[rgba(193,85,43,0.16)]" placeholder="••••••••••" />
            </div>

            <button type="submit" disabled={loading} className="mt-2 h-12 w-full rounded-[10px] bg-[var(--accent)] text-[15px] font-semibold text-white transition hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-60">
              {loading ? 'Entrando…' : 'Entrar'}
            </button>

            {error ? <p className="rounded-[10px] border border-[rgba(193,85,43,0.2)] bg-[rgba(193,85,43,0.08)] px-3.5 py-2.5 text-[13px] text-[#9e4120]">{error}</p> : null}
          </form>

          <p className="mt-7 text-center text-[13px] text-[var(--label)]">Acesso restrito a usuários autorizados.</p>

          <div className="mt-4 flex items-center justify-center gap-3 text-[13px] text-[var(--muted)]">
            <button type="button" onClick={onDemoLogin} className="transition hover:text-[var(--ink)]">
              Entrar com demo
            </button>
            <span className="text-[var(--label)]">·</span>
            <button type="button" onClick={onLocalDemo} className="transition hover:text-[var(--ink)]">
              Modo local
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
