import logging

from typing import Any
from datetime import timedelta

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import STATE_ON, STATE_OFF


from .config_flow import SUPPORTED_FUNCTION
from . import DOMAIN, DeviceBase
from .climate import GreeClimate

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    config = config_entry.data
    _LOGGER.info(f'Adding Gree climate switch {config["function"]} to hass...')
    async_add_entities([
        GreeSwitch(hass, func, config["name"], config["mac_addr"])
        for func in config["function"]
    ], True)

class GreeSwitch(DeviceBase, SwitchEntity):

    def __init__(self, hass: HomeAssistant, func: str, name: str, mac_addr: str) -> None:
        super().__init__(name, mac_addr)
        SwitchEntity.__init__(self)
        self._func = func
        self._attr_unique_id = f'switch.gree_{self._mac_addr}_{func}'
        self.entity_id = self._entity_common_perfix + "_" + self._func

    def _get_device_object(self) -> GreeClimate:
        return self.hass.data[DOMAIN].get(self._mac_addr, None)

    @property
    def device_class(self) -> SwitchDeviceClass:
        return SwitchDeviceClass.SWITCH

    @property
    def icon(self) -> str:
        return {
            "lights": "mdi:lightbulb-on-10",
            "health": "mdi:pine-tree-variant-outline",
            "powersave": "mdi:leaf-circle-outline",
            "sleep": "mdi:power-sleep",
            "xfan": "mdi:tumble-dryer",
            "eightdegheat": "mdi:dice-d8-outline",
            "air": "mdi:weather-dust"
        }[self._func]
    
    @property
    def name(self):
        return SUPPORTED_FUNCTION[self._func]

    @property
    def is_on(self) -> bool:
        if dev := self._get_device_object():
            return {
                "lights": dev._current_lights,
                "health": dev._current_health,
                "powersave": dev._current_powersave,
                "sleep": dev._current_sleep,
                "xfan": dev._current_xfan,
                "eightdegheat": dev._current_eightdegheat,
                "air": dev._current_air
            }[self._func] == STATE_ON
        return False
    
    def _async_toggle_switch(self, on: bool):
        if dev := self._get_device_object():
            st = int(on)
            dev.SyncState({
                "lights": {"Lig": st},
                "health": {"Health": st},
                "powersave": {"SvSt": st},
                "sleep": {'SwhSlp': st, 'SlpMod': st},
                "xfan": {"Blo": st},
                "eightdegheat": {"StHt": st},
                "air": {"Air": st}
            }[self._func])   

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._async_toggle_switch(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._async_toggle_switch(False)
        self.async_write_ha_state()

    