"""
Sentry + PostHog setup (build plan A2 §17 + §9 Day 22).

Sampling per A2 §9 cost note: traces at 10%, errors at 100%. Stays under
the free 5K events/mo at v1 traffic; one bad deploy doesn't burn the
whole monthly budget.

Privacy: send_default_pii=False — no IP capture, no cookies, no headers
beyond what we explicitly attach. Day 26 security review tunes whether
we set hashed user_id via Sentry.set_user().
"""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def init_sentry() -> bool:
    """Returns True if Sentry was initialised, False if no DSN configured."""
    if not settings.sentry_dsn_backend:
        logger.info("Sentry disabled (no SENTRY_DSN_BACKEND)")
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn_backend,
            environment=settings.app_env,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.0,
            send_default_pii=False,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                StarletteIntegration(transaction_style="endpoint"),
            ],
            release=f"aria-api@{settings.app_env}",
        )
        logger.info("Sentry initialised at 10%% trace sample rate")
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Sentry init failed — continuing without observability")
        return False
