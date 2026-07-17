import { Logo } from '../../components/ui/brand'

const navItems = [
  { label: 'Produto', id: 'produto' },
  { label: 'Como funciona', id: 'como-funciona' },
  { label: 'Segurança', id: 'seguranca' },
] as const

const flowSteps = [
  { title: 'Detecção na borda', text: 'Edge workers leem câmeras e enviam apenas eventos de risco — sem vídeo contínuo.' },
  { title: 'Triagem no dashboard', text: 'O evento vira incidente priorizado e chega à equipe certa para resposta rápida.' },
  { title: 'Registro auditável', text: 'Ação, evidência e histórico ficam registrados para auditoria e conformidade.' },
] as const

const securityPoints = [
  { title: 'Sem reconhecimento facial', text: 'Nenhuma identificação biométrica no MVP.' },
  { title: 'Sem vídeo contínuo', text: 'Apenas eventos e evidências curtas quando necessário.' },
  { title: 'Evidências privadas', text: 'Isoladas por organização, com URLs assinadas e auditoria de acesso.' },
  { title: 'Auditoria completa', text: 'Trilha de ações sensíveis e retenção configurável por organização.' },
] as const

const features = [
  {
    eyebrow: 'Monitoramento',
    title: 'Enxergue o risco antes do acidente',
    description: 'Leitura contínua do ambiente, com foco em prevenção, triagem e resposta rápida.',
  },
  {
    eyebrow: 'Operação',
    title: 'Fluxo simples para equipes reais',
    description: 'Alertas diretos, contexto claro e acesso restrito para quem precisa agir.',
  },
  {
    eyebrow: 'Auditoria',
    title: 'Rastro limpo para conformidade',
    description: 'Eventos organizados, decisões rastreáveis e histórico pronto para revisão.',
  },
] as const

export function LandingPage({ onLogin, onScrollToSection }: { onLogin: () => void; onScrollToSection: (id: string) => void }) {
  return (
    <div className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col px-5 sm:px-6 lg:px-8">
      <header className="reveal flex items-center justify-between gap-4 border-b border-[color:var(--line)] py-5">
        <button type="button" onClick={() => onScrollToSection('top')} className="text-left">
          <Logo size="md" markClassName="h-9 w-9" />
        </button>

        <nav className="hidden items-center gap-8 text-[15px] text-[#57524b] md:flex">
          {navItems.map((item) => (
            <button key={item.id} type="button" onClick={() => onScrollToSection(item.id)} className="transition hover:text-[var(--ink)]">
              {item.label}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-3 sm:gap-5">
          <button type="button" onClick={onLogin} className="text-[15px] font-medium text-[var(--ink)] transition hover:text-[var(--accent)]">
            Entrar
          </button>
          <button type="button" onClick={onLogin} className="rounded-lg bg-[var(--ink)] px-4 py-2.5 text-[15px] font-medium text-[var(--paper)] transition hover:bg-[var(--ink-soft)]">
            Solicitar demonstração
          </button>
        </div>
      </header>

      <section id="top" className="flex flex-1 flex-col items-center justify-center py-24 text-center lg:py-32">
        <p className="reveal font-mono-ui text-xs uppercase tracking-[0.24em] text-[var(--muted-2)]">Segurança do trabalho · visão computacional</p>
        <h1 className="reveal mt-8 max-w-[15ch] font-display text-5xl font-bold leading-[0.98] tracking-[-0.04em] text-[var(--ink)] sm:text-6xl lg:text-7xl" style={{ animationDelay: '120ms' }}>
          Enxergue o risco antes do acidente
        </h1>
        <p className="reveal mt-7 max-w-[600px] text-lg leading-relaxed text-[var(--muted)] sm:text-xl" style={{ animationDelay: '220ms' }}>
          Visão computacional na borda transforma eventos de risco em incidentes auditáveis — com evidências privadas e isolamento por organização.
        </p>
        <div className="reveal mt-11 flex flex-wrap items-center justify-center gap-6" style={{ animationDelay: '320ms' }}>
          <button type="button" onClick={onLogin} className="rounded-lg bg-[var(--accent)] px-7 py-3.5 text-base font-semibold text-white transition hover:bg-[var(--accent-hover)]">
            Solicitar demonstração
          </button>
          <button type="button" onClick={() => onScrollToSection('como-funciona')} className="inline-flex items-center gap-2 text-base font-medium text-[var(--ink)] transition hover:text-[var(--accent)]">
            Ver como funciona
            <span className="font-mono-ui text-[var(--accent)]">→</span>
          </button>
        </div>
      </section>

      <section id="produto" className="grid gap-5 border-t border-[color:var(--line)] py-16 lg:grid-cols-3">
        {features.map((feature, index) => (
          <article key={feature.title} className="reveal rounded-[10px] border border-[color:var(--line)] bg-[var(--card)] p-6" style={{ animationDelay: `${100 * (index + 1)}ms` }}>
            <p className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-[var(--accent)]">{feature.eyebrow}</p>
            <h3 className="mt-3 font-display text-xl font-semibold text-[var(--ink)]">{feature.title}</h3>
            <p className="mt-2.5 text-sm leading-6 text-[var(--muted)]">{feature.description}</p>
          </article>
        ))}
      </section>

      <section id="como-funciona" className="border-t border-[color:var(--line)] py-16">
        <div className="max-w-2xl">
          <p className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-[var(--accent)]">Como funciona</p>
          <h2 className="mt-3 font-display text-3xl font-bold tracking-[-0.02em] text-[var(--ink)] md:text-4xl">Da câmera ao incidente auditável</h2>
          <p className="mt-4 text-base leading-7 text-[var(--muted)]">Fluxo direto: detecção na borda, triagem no dashboard e registro completo para auditoria.</p>
        </div>
        <ol className="mt-10 grid gap-4 md:grid-cols-3">
          {flowSteps.map((step, index) => (
            <li key={step.title} className="reveal rounded-[10px] border border-[color:var(--line)] bg-[var(--card)] p-6" style={{ animationDelay: `${100 * (index + 1)}ms` }}>
              <span className="font-mono-ui text-sm text-[var(--accent)]">0{index + 1}</span>
              <h3 className="mt-3 font-display text-lg font-semibold text-[var(--ink)]">{step.title}</h3>
              <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section id="seguranca" className="border-t border-[color:var(--line)] py-16">
        <div className="max-w-2xl">
          <p className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-[var(--accent)]">Segurança e privacidade</p>
          <h2 className="mt-3 font-display text-3xl font-bold tracking-[-0.02em] text-[var(--ink)] md:text-4xl">Feito para segurança do trabalho, não para vigilância</h2>
          <p className="mt-4 text-base leading-7 text-[var(--muted)]">Privacidade desde a fundação: mínimo necessário de dados, evidências isoladas por organização e trilha auditável.</p>
        </div>
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {securityPoints.map((point) => (
            <article key={point.title} className="rounded-[10px] border border-[color:var(--line)] bg-[var(--card)] p-6">
              <h3 className="font-display text-lg font-semibold text-[var(--ink)]">{point.title}</h3>
              <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{point.text}</p>
            </article>
          ))}
        </div>
      </section>

      <footer className="flex flex-col items-center gap-4 border-t border-[color:var(--line)] py-8 text-sm text-[var(--muted)] sm:flex-row sm:justify-between">
        <div className="flex items-center gap-2.5">
          <Logo size="sm" markClassName="h-6 w-6" />
          <span>VigIA Safety · segurança industrial assistida por visão computacional.</span>
        </div>
        <button type="button" onClick={onLogin} className="font-medium text-[var(--ink)] transition hover:text-[var(--accent)]">
          Entrar
        </button>
      </footer>
    </div>
  )
}
