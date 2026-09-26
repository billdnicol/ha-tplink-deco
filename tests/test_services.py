"""Tests for the set_client_blocked service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.tplink_deco.api.errors import TpLinkDecoApiClientError
from custom_components.tplink_deco.const import (
    ATTR_BLOCKED,
    ATTR_MAC,
    DOMAIN,
    SERVICE_SET_CLIENT_BLOCKED,
)
from custom_components.tplink_deco.services import TpLinkDecoBlockService


def _hass_with_entry(state: ConfigEntryState = ConfigEntryState.LOADED) -> MagicMock:
    """Return a mock hass exposing one config entry in the given state."""
    api_client = MagicMock()
    entry = MagicMock(state=state, runtime_data=MagicMock(client=api_client))
    hass = MagicMock()
    hass.config_entries.async_entries.return_value = [entry]
    hass.services.has_service.return_value = False

    async def _executor(func: object) -> object:
        return func()

    hass.async_add_executor_job = AsyncMock(side_effect=_executor)
    return hass


def _call(mac: str = "AA:BB:CC:DD:EE:FF", *, blocked: bool = True) -> MagicMock:
    """Build a mock ServiceCall carrying the given field values."""
    return MagicMock(data={ATTR_MAC: mac, ATTR_BLOCKED: blocked})


async def test_async_register_registers_the_service() -> None:
    """Registering wires the handler under the domain and service name."""
    hass = _hass_with_entry()
    TpLinkDecoBlockService(hass).async_register()
    hass.services.async_register.assert_called_once()
    args = hass.services.async_register.call_args.args
    assert args[0] == DOMAIN
    assert args[1] == SERVICE_SET_CLIENT_BLOCKED


async def test_async_register_is_idempotent() -> None:
    """A second registration is skipped when the service already exists."""
    hass = _hass_with_entry()
    hass.services.has_service.return_value = True
    TpLinkDecoBlockService(hass).async_register()
    hass.services.async_register.assert_not_called()


async def test_async_unregister_removes_the_service() -> None:
    """Unregistering removes the handler under the domain and service name."""
    hass = _hass_with_entry()
    TpLinkDecoBlockService(hass).async_unregister()
    hass.services.async_remove.assert_called_once_with(
        DOMAIN, SERVICE_SET_CLIENT_BLOCKED
    )


async def test_handle_calls_the_loaded_entrys_client() -> None:
    """The handler blocks/unblocks through the first loaded entry's client."""
    hass = _hass_with_entry()
    entry = hass.config_entries.async_entries.return_value[0]
    service = TpLinkDecoBlockService(hass)
    await service._async_handle(_call("AA:BB:CC:DD:EE:FF", blocked=True))
    entry.runtime_data.client.set_client_blocked.assert_called_once_with(
        "AA:BB:CC:DD:EE:FF", blocked=True
    )


async def test_handle_raises_when_no_entry_is_loaded() -> None:
    """A call with nothing loaded fails validation instead of crashing."""
    hass = _hass_with_entry(state=ConfigEntryState.NOT_LOADED)
    service = TpLinkDecoBlockService(hass)
    with pytest.raises(ServiceValidationError):
        await service._async_handle(_call())


async def test_handle_wraps_client_errors() -> None:
    """A client-layer failure surfaces as a HomeAssistantError, not a raw one."""
    hass = _hass_with_entry()
    entry = hass.config_entries.async_entries.return_value[0]
    entry.runtime_data.client.set_client_blocked.side_effect = TpLinkDecoApiClientError(
        "boom"
    )
    service = TpLinkDecoBlockService(hass)
    with pytest.raises(HomeAssistantError):
        await service._async_handle(_call())
