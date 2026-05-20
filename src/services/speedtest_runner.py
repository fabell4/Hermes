"""SpeedtestRunner — orchestrates test providers with automatic fallback."""

from __future__ import annotations

import logging

from src import config
from src.constants import ProviderType
from src.models.speed_result import SpeedResult
from src.providers.base import BaseTestProvider
from src.providers.custom_http import CustomHttpProvider
from src.providers.ndt7 import NDT7Provider
from src.providers.ookla import OoklaProvider

_log = logging.getLogger(__name__)


class SpeedtestRunner:
    """Orchestrates speed test providers with automatic fallback.

    Tries each provider in order. The primary provider (index 0) is retried once
    on transient failure before falling back to the next provider. Subsequent
    providers are tried once each.

    When called with no arguments, builds the provider list from
    SPEEDTEST_PROVIDERS, SPEEDTEST_SERVER_ID, and SPEEDTEST_CUSTOM_URL_* config.
    """

    def __init__(
        self,
        speedtest_path: str | None = None,
        server_id: int | None = None,
        providers: list[BaseTestProvider] | None = None,
    ) -> None:
        """
        Initialize the runner.

        Args:
            speedtest_path: Passed to OoklaProvider. Ignored when providers is given.
            server_id: Overrides config.SPEEDTEST_SERVER_ID for OoklaProvider.
                       Pass None to use the configured default.
            providers: Explicit ordered list of providers (used in tests). When
                       supplied, speedtest_path and server_id are ignored.
        """
        self._speedtest_path = speedtest_path
        # Explicit server_id overrides config; None defers to config.
        self._server_id = server_id if server_id is not None else config.SPEEDTEST_SERVER_ID
        if providers is not None:
            self._providers = providers
        else:
            self._providers = self._build_providers()

    def _build_providers(self) -> list[BaseTestProvider]:
        """Build the provider list from SPEEDTEST_PROVIDERS config."""
        providers: list[BaseTestProvider] = []
        for name in config.SPEEDTEST_PROVIDERS:
            if name == ProviderType.OOKLA:
                providers.append(
                    OoklaProvider(
                        speedtest_path=self._speedtest_path,
                        server_id=self._server_id,
                    )
                )
            elif name == ProviderType.NDT7:
                providers.append(NDT7Provider())
            elif name == ProviderType.CUSTOM:
                providers.append(
                    CustomHttpProvider(
                        download_url=config.SPEEDTEST_CUSTOM_URL_DOWNLOAD,
                        upload_url=config.SPEEDTEST_CUSTOM_URL_UPLOAD,
                        duration_s=config.SPEEDTEST_CUSTOM_DURATION_S,
                        connections=config.SPEEDTEST_CUSTOM_CONNECTIONS,
                        chunk_size_mb=config.SPEEDTEST_CUSTOM_CHUNK_SIZE_MB,
                    )
                )
        if not providers:
            # Should not happen due to config validation, but be defensive
            _log.warning("No valid providers found in config; defaulting to Ookla.")
            providers.append(
                OoklaProvider(
                    speedtest_path=self._speedtest_path,
                    server_id=self._server_id,
                )
            )
        return providers

    def _attempt_provider(
        self, provider: BaseTestProvider, is_primary: bool
    ) -> SpeedResult:
        """Try a single provider, retrying once if it is the primary.

        Raises:
            RuntimeError: If all attempts for this provider fail.
        """
        attempts = 2 if is_primary else 1
        last_exc: RuntimeError | None = None
        for attempt in range(attempts):
            try:
                return provider.run()
            except RuntimeError as exc:
                last_exc = exc
                if is_primary and attempt == 0:
                    _log.warning(
                        "Provider '%s' attempt 1 failed (%s) — retrying.",
                        provider.name,
                        exc,
                    )
        assert last_exc is not None  # always set: loop runs ≥ 1 times
        raise last_exc

    def run(self) -> SpeedResult:
        """Run the speed test, trying providers in order with fallback.

        The primary provider is retried once on failure. All subsequent providers
        are attempted once each. Raises RuntimeError if every provider fails.
        """
        if not self._providers:
            raise RuntimeError("No test providers configured.")

        last_exc: Exception | None = None
        for i, provider in enumerate(self._providers):
            try:
                return self._attempt_provider(provider, is_primary=(i == 0))
            except RuntimeError as exc:
                last_exc = exc
                if i + 1 < len(self._providers):
                    _log.warning(
                        "Provider '%s' failed — falling back to '%s'.",
                        provider.name,
                        self._providers[i + 1].name,
                    )

        if last_exc is None:  # pragma: no cover
            raise RuntimeError("Speedtest failed with no recorded exception.")
        raise last_exc
