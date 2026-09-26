"""Service to block or unblock a client device by MAC address."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .api.errors import TpLinkDecoApiClientError
from .const import ATTR_BLOCKED, ATTR_MAC, DOMAIN, LOGGER, SERVICE_SET_CLIENT_BLOCKED

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

SERVICE_SET_CLIENT_BLOCKED_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MAC): cv.string,
        vol.Required(ATTR_BLOCKED): cv.boolean,
    }
)


class TpLinkDecoBlockService:
    """Registers the domain-wide set_client_blocked service."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Bind the service registration to a Home Assistant instance."""
        self._hass = hass

    def async_register(self) -> None:
        """Register the service if it isn't already registered by another entry."""
        if self._hass.services.has_service(DOMAIN, SERVICE_SET_CLIENT_BLOCKED):
            return
        self._hass.services.async_register(
            DOMAIN,
            SERVICE_SET_CLIENT_BLOCKED,
            self._async_handle,
            schema=SERVICE_SET_CLIENT_BLOCKED_SCHEMA,
        )

    def async_unregister(self) -> None:
        """Remove the service."""
        self._hass.services.async_remove(DOMAIN, SERVICE_SET_CLIENT_BLOCKED)

    async def _async_handle(self, call: ServiceCall) -> None:
        """
        Block or unblock the given MAC on the first loaded config entry's router.

        A household is assumed to run a single Deco mesh — with more than one
        config entry loaded, the first one found handles every call.
        """
        entries = self._hass.config_entries.async_entries(DOMAIN)
        loaded = next(
            (entry for entry in entries if entry.state == ConfigEntryState.LOADED),
            None,
        )
        if loaded is None:
            message = "No TP-Link Deco config entry is loaded"
            raise ServiceValidationError(message)

        mac = call.data[ATTR_MAC]
        blocked = call.data[ATTR_BLOCKED]
        try:
            await self._hass.async_add_executor_job(
                partial(
                    loaded.runtime_data.client.set_client_blocked, mac, blocked=blocked
                )
            )
        except TpLinkDecoApiClientError as exception:
            LOGGER.error("Failed to set blocked=%s for %s: %s", blocked, mac, exception)
            message = f"Failed to update block state for {mac}: {exception}"
            raise HomeAssistantError(message) from exception
