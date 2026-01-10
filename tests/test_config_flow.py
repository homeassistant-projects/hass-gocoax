"""Tests for goCoax MoCA config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.gocoax.const import DOMAIN
from custom_components.gocoax.pygocoax.exceptions import (
    GoCoaxAuthError,
    GoCoaxConnectionError,
)

from .conftest import MOCK_HOST, MOCK_MAC, MOCK_PASSWORD, MOCK_USERNAME


async def test_user_flow_success(
    hass: HomeAssistant,
    mock_gocoax_client,  # noqa: ARG001
) -> None:
    """Test successful user config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: MOCK_HOST,
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == f"goCoax ({MOCK_HOST})"
    assert result["data"] == {
        CONF_HOST: MOCK_HOST,
        CONF_USERNAME: MOCK_USERNAME,
        CONF_PASSWORD: MOCK_PASSWORD,
    }
    assert result["result"].unique_id == MOCK_MAC


async def test_user_flow_cannot_connect(
    hass: HomeAssistant,
) -> None:
    """Test user flow when connection fails."""
    with patch(
        "custom_components.gocoax.config_flow.GoCoaxClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.get_mac_address = AsyncMock(
            side_effect=GoCoaxConnectionError("Connection failed")
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: MOCK_HOST,
                CONF_USERNAME: MOCK_USERNAME,
                CONF_PASSWORD: MOCK_PASSWORD,
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_invalid_auth(
    hass: HomeAssistant,
) -> None:
    """Test user flow when authentication fails."""
    with patch(
        "custom_components.gocoax.config_flow.GoCoaxClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.get_mac_address = AsyncMock(
            side_effect=GoCoaxAuthError("Auth failed")
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: MOCK_HOST,
                CONF_USERNAME: MOCK_USERNAME,
                CONF_PASSWORD: "wrong_password",
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_duplicate(
    hass: HomeAssistant,
    mock_gocoax_client,  # noqa: ARG001
    mock_config_entry_data,
) -> None:
    """Test user flow when adapter is already configured."""
    # create existing entry
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title=f"goCoax ({MOCK_HOST})",
        data=mock_config_entry_data,
        source=config_entries.SOURCE_USER,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: MOCK_HOST,
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
        },
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(
    hass: HomeAssistant,
    mock_config_entry_data,
) -> None:
    """Test options flow."""
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title=f"goCoax ({MOCK_HOST})",
        data=mock_config_entry_data,
        source=config_entries.SOURCE_USER,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"scan_interval": 60},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {"scan_interval": 60}
