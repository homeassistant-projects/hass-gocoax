"""Config flow for goCoax MoCA integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .pygocoax import GoCoaxClient
from .pygocoax.exceptions import GoCoaxAuthError, GoCoaxConnectionError

LOG = logging.getLogger(__name__)


class GoCoaxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for goCoax MoCA."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._host: str | None = None
        self._username: str | None = None
        self._password: str | None = None
        self._mac_address: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GoCoaxOptionsFlow:
        """Get the options flow for this handler."""
        return GoCoaxOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._username = user_input.get(CONF_USERNAME, DEFAULT_USERNAME)
            self._password = user_input.get(CONF_PASSWORD, DEFAULT_PASSWORD)

            # validate connection
            error = await self._async_validate_connection()
            if error:
                errors["base"] = error
            else:
                # check for duplicate entry
                await self.async_set_unique_id(self._mac_address)
                self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})

                return self.async_create_entry(
                    title=f"goCoax ({self._host})",
                    data={
                        CONF_HOST: self._host,
                        CONF_USERNAME: self._username,
                        CONF_PASSWORD: self._password,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                    vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                    vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle reauth when authentication fails."""
        self._host = entry_data[CONF_HOST]
        self._username = entry_data.get(CONF_USERNAME, DEFAULT_USERNAME)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input.get(CONF_USERNAME, self._username)
            self._password = user_input.get(CONF_PASSWORD)

            error = await self._async_validate_connection()
            if error:
                errors["base"] = error
            else:
                # update existing entry
                entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                if entry:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            CONF_USERNAME: self._username,
                            CONF_PASSWORD: self._password,
                        },
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_USERNAME, default=self._username): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
            description_placeholders={"host": self._host},
        )

    async def _async_validate_connection(self) -> str | None:
        """Validate connection to goCoax adapter."""
        session = async_get_clientsession(self.hass)
        client = GoCoaxClient(
            host=self._host,
            username=self._username,
            password=self._password,
            session=session,
        )

        try:
            self._mac_address = await client.get_mac_address()
            if not self._mac_address:
                return "cannot_connect"
            return None
        except GoCoaxAuthError:
            return "invalid_auth"
        except GoCoaxConnectionError:
            return "cannot_connect"
        except Exception:
            LOG.exception("Unexpected error during connection validation")
            return "unknown"


class GoCoaxOptionsFlow(OptionsFlow):
    """Handle options flow for goCoax."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=current_interval
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=5,
                            unit_of_measurement="seconds",
                            mode=NumberSelectorMode.SLIDER,
                        )
                    ),
                }
            ),
        )
