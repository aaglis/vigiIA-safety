from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from typing import Any, Protocol


class NotificationSendError(RuntimeError):
    pass


class Notifier(Protocol):
    channel: str

    def send(self, *, subject: str, body: str, recipients: list[str]) -> None: ...


def _sanitize_error(exc: Exception, api_key: str | None = None) -> str:
    """Mensagem de erro sem segredo: a chave do Resend nunca pode ir para log/payload."""
    message = str(exc) or exc.__class__.__name__
    if api_key:
        message = message.replace(api_key, "***")
    message = re.sub(r"re_[A-Za-z0-9_\-]+", "***", message)
    return message[:200]


def is_resend_configured(settings_obj: Any) -> bool:
    key = (getattr(settings_obj, "resend_api_key", "") or "").strip()
    return bool(key) and "dev-only" not in key.lower() and "change-me" not in key.lower()


@dataclass
class MockNotifier:
    """Não envia nada. Usado em dev/teste e quando não há chave configurada."""

    channel: str = "mock"

    def send(self, *, subject: str, body: str, recipients: list[str]) -> None:
        return None


@dataclass
class ResendNotifier:
    api_key: str
    sender: str
    channel: str = "email"

    def send(self, *, subject: str, body: str, recipients: list[str]) -> None:
        if not recipients:
            raise NotificationSendError("no recipients configured")
        try:
            import resend  # type: ignore
        except Exception as exc:  # pragma: no cover - depende do ambiente ter o SDK
            raise NotificationSendError("resend sdk unavailable") from exc
        resend.api_key = self.api_key
        try:
            resend.Emails.send({"from": self.sender, "to": recipients, "subject": subject, "html": body})
        except Exception as exc:
            raise NotificationSendError(_sanitize_error(exc, self.api_key)) from exc


def build_notifier(settings_obj: Any) -> Notifier:
    """Resend quando há chave real e modo `resend`; caso contrário, mock (nunca quebra o fluxo)."""
    mode = (getattr(settings_obj, "incident_notification_mode", "mock") or "mock").strip().lower()
    if mode == "resend" and is_resend_configured(settings_obj):
        return ResendNotifier(api_key=settings_obj.resend_api_key, sender=getattr(settings_obj, "notification_from", ""))
    return MockNotifier()


def build_incident_email(incident: Any, *, dashboard_url: str | None = None) -> tuple[str, str]:
    severity = str(getattr(incident, "severity", "")).upper()
    summary = str(getattr(incident, "summary", None) or "Incidente de segurança detectado")
    subject = f"[VigIA] {severity} — {summary}"
    rows = {
        "Severidade": severity,
        "Resumo": summary,
        "Câmera": getattr(incident, "camera_id", "—"),
        "Zona": getattr(incident, "zone_id", "—"),
        "Site": getattr(incident, "site_id", "—"),
        "Detectado em": getattr(incident, "created_at", "—"),
    }
    lines = "".join(f"<tr><td><b>{escape(str(key))}</b></td><td>{escape(str(value))}</td></tr>" for key, value in rows.items())
    link = ""
    if dashboard_url:
        escaped_url = escape(dashboard_url, quote=True)
        if dashboard_url.startswith(("http://", "https://")):
            link = f'<p><a href="{escaped_url}" rel="noreferrer noopener">Abrir no dashboard</a></p>'
    body = f"<h2>{escape(subject)}</h2><table>{lines}</table>{link}"
    return subject, body
