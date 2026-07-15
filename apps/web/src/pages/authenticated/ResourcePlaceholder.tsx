export function ResourcePlaceholder({ title, description, bullets, activeLabel, liveLabel, activeOrganization, userName }: { title: string; description: string; bullets: string[]; activeLabel: string; liveLabel: string; activeOrganization: string; userName: string }) {
  return (
    <section className="space-y-6">
      <div className="rounded-[34px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.92)] p-6 shadow-[0_22px_60px_rgba(32,27,24,0.08)]">
        <p className="font-mono-ui text-[11px] uppercase tracking-[0.3em] text-[var(--accent)]">{activeLabel}</p>
        <h1 className="mt-3 font-display text-3xl leading-tight text-[var(--ink)] sm:text-4xl">{title}</h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--muted)]">{description}</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-[30px] border border-[color:var(--line)] bg-[var(--card)] p-6 shadow-[0_18px_50px_rgba(32,27,24,0.06)]">
          <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[var(--accent)]">Em construção</p>
          <ul className="mt-4 space-y-3 text-sm leading-7 text-[var(--muted)]">{bullets.map((bullet) => <li key={bullet} className="flex gap-3 rounded-[18px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.56)] px-4 py-3"><span className="mt-1 h-2 w-2 rounded-full bg-[var(--accent)]" /><span>{bullet}</span></li>)}</ul>
        </article>
        <aside className="rounded-[30px] border border-[color:var(--line)] bg-[rgba(32,27,24,0.96)] p-6 text-[var(--paper)] shadow-[0_24px_70px_rgba(32,27,24,0.16)]">
          <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[rgba(245,243,239,0.7)]">Contexto</p>
          <div className="mt-4 space-y-3 text-sm leading-7 text-[rgba(245,243,239,0.84)]"><p>Organização ativa: {activeOrganization}</p><p>Usuário: {userName}</p><p>Status: {liveLabel}</p></div>
          <div className="mt-6 rounded-[24px] border border-white/10 bg-white/5 p-4 text-sm text-[rgba(245,243,239,0.74)]">Este espaço já segue o shell autenticado, então quando a tela ganhar CRUD real a navegação continuará intacta.</div>
        </aside>
      </div>
    </section>
  )
}
