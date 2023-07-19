from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.components.climate.const import (
    HVAC_MODE_OFF, HVAC_MODE_AUTO, HVAC_MODE_COOL, HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY, HVAC_MODE_HEAT,
    FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH)

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback, HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

from .climate import GreeClimate
from . import DOMAIN

SUPPORTED_FUNCTION = {
    "lights": "指示灯",
    "health": "健康",
    "powersave": "节能",
    "sleep": "睡眠",
    "xfan": "烘干",
    "eightdegheat": "8度加热",
    "air": "送风"
}

EXTRA_HVAC_MODES = {
    HVAC_MODE_AUTO: "自动", 
    HVAC_MODE_COOL: "制冷",
    HVAC_MODE_HEAT: "制热",
    HVAC_MODE_DRY: "除湿", 
    HVAC_MODE_FAN_ONLY: "送风"
}

FAN_MODES = {
    FAN_AUTO: "自动", 
    FAN_LOW: "低风", 
    'Medium-Low': "中低风", 
    FAN_MEDIUM: "中风", 
    'Medium-High': "中高风", 
    FAN_HIGH: "高风", 
    'Turbo': "强劲", 
    'Quiet': "静音"
}

DEFAULT_FUNCTION = ["lights", "health", "sleep"]
DEFAULT_HVAC_MODES = [HVAC_MODE_AUTO, HVAC_MODE_COOL, HVAC_MODE_HEAT]
DEFAULT_FAN_MODES = [FAN_AUTO, FAN_LOW, 'Medium-Low', FAN_MEDIUM, 'Medium-High', FAN_HIGH, 'Turbo', 'Quiet']
DEFAULT_TIMEOUT = 10
DEFAULT_TARGET_TEMP_STEP = 0.5

def _check_input(input: dict) -> str:
    if not re.match(r"^(2(5[0-5]|[0-4]\d)|1\d{2}|[1-9]?\d)(\.(2(5[0-5]|[0-4]\d)|1\d{2}|[1-9]?\d)){3}$", input.get("host", "")):
        return "ip_format_error"
    if not 0 <= input.get("port", -1) <= 65535:
        return "port_error"
    if not re.match(r"^[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}$", input.get("mac_addr", "")):
        return "mac_addr_format_error"
    return ""

def _async_get_matching_entities(
    hass: HomeAssistant,
    domains: list[str] | None = None
) -> dict[str, str]:
    return {
        state.entity_id: (
            f"{state.attributes.get('friendly_name', state.entity_id)} ({state.entity_id})"
        )
        for state in sorted(
            hass.states.async_all(domains and set(domains)),
            key=lambda item: item.entity_id
        )
    }

def _get_data_schema(hass: HomeAssistant, user_input: dict, options: bool=False) -> dict:
    all_sensor = _async_get_matching_entities(hass, ["sensor"])
    data_schema = {}
    if not options:
        data_schema.update({
            vol.Required("host", default=user_input.get("host", vol.UNDEFINED)): str,
            vol.Required("port", default=user_input.get("port", 7000)): int,
            vol.Required("mac_addr", default=user_input.get("mac_addr", vol.UNDEFINED)): str
        })
    data_schema.update({
            vol.Optional("name", default=user_input.get("name", vol.UNDEFINED)): str,
            vol.Required("temp_step", default=user_input.get("temp_step", DEFAULT_TARGET_TEMP_STEP)): vol.Coerce(float),
            vol.Optional("temp_sensor", default=user_input.get("temp_sensor", vol.UNDEFINED)): vol.In(all_sensor),
            vol.Optional("function", default=user_input.get("function", DEFAULT_FUNCTION)): cv.multi_select(SUPPORTED_FUNCTION),
            vol.Optional("hvac_modes", default=user_input.get("hvac_modes", DEFAULT_HVAC_MODES)): cv.multi_select(EXTRA_HVAC_MODES),
            vol.Optional("fan_modes", default=user_input.get("fan_modes", DEFAULT_FAN_MODES)): cv.multi_select(FAN_MODES),
            vol.Optional("encryption_key", default=user_input.get("encryption_key", vol.UNDEFINED)): str,
            vol.Optional("uid", default=user_input.get("uid", vol.UNDEFINED)): int,
            vol.Required("timeout", default=user_input.get("timeout", DEFAULT_TIMEOUT)): int
        })
    return data_schema

class GreeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return GreeOptionsFlow(entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        return await self.async_step_info()

    async def async_step_info(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors = {}
        if user_input is None:
            user_input = {}
        if "host" in user_input and "port" in user_input:
            res = _check_input(user_input)
            if not res:
                try:
                    device = GreeClimate(self.hass, **user_input)
                    await self.async_set_unique_id(device._mac_addr)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=device.name,
                        data=user_input,
                    )
                except Exception as e:
                    errors["base"] = "device_not_found"
                    import traceback
                    _LOGGER.error(traceback.format_exc())
            else:
                errors["base"] = res
        return self.async_show_form(
            step_id="info",
            data_schema=vol.Schema(_get_data_schema(self.hass, user_input)),
            errors=errors
        )


class GreeOptionsFlow(config_entries.OptionsFlow):

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_info(self.config_entry.data)

    async def async_step_info(self, user_input=None):
        errors = {}
        data = self.config_entry.data
        if "host" not in user_input:
            user_input.update({
                "host": data["host"],
                "port": data["port"],
                "mac_addr": data["mac_addr"]
            })
            try:
                device = GreeClimate(self.hass, **user_input)
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=user_input
                )
                return self.async_create_entry(
                    title=device.name,
                    data=user_input,
                )
            except Exception as e:
                errors["base"] = "device_not_found"
                import traceback
                _LOGGER.error(traceback.format_exc())
        return self.async_show_form(
            step_id='info',
            data_schema=vol.Schema(_get_data_schema(self.hass, user_input, True)),
            description_placeholders={
                "ip": f'{data["host"]}:{data["port"]}',
                "mac": data["mac_addr"]
            },
            errors=errors,
        )