import logging

from datetime import timedelta

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF, HVAC_MODE_AUTO, HVAC_MODE_COOL, HVAC_MODE_DRY, HVAC_MODE_FAN_ONLY, HVAC_MODE_HEAT, 
    SWING_BOTH, SWING_HORIZONTAL, SWING_OFF, SWING_VERTICAL,
    FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH
)

from ..gree.climate import GreeClimate as GreeClimateBase
from . import DOMAIN, DeviceBase

REQUIREMENTS = ['pycryptodome']

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [HVAC_MODE_AUTO, HVAC_MODE_COOL, HVAC_MODE_DRY, HVAC_MODE_FAN_ONLY, HVAC_MODE_HEAT, HVAC_MODE_OFF]
FAN_MODES = [FAN_AUTO, FAN_LOW, 'Medium-Low', FAN_MEDIUM, 'Medium-High', FAN_HIGH, 'Turbo', 'Quiet']
SWING_MODES = [SWING_OFF, SWING_VERTICAL, SWING_HORIZONTAL, SWING_BOTH]
DEFAULT_HVAC_MODES = [HVAC_MODE_OFF]

SCAN_INTERVAL = timedelta(seconds=5)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    _LOGGER.info('Adding Gree climate device to hass...')
    config = config_entry.data
    dev = GreeClimate(hass, **config)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(dev._mac_addr, dev)
    async_add_entities([dev], True)

def _sort_by_list(source: list, leads: list) -> list:
    return [
        item
        for item in leads
        if item in source
    ]

class GreeClimate(DeviceBase, GreeClimateBase):

    def __init__(self, hass, **kwargs):
        super().__init__(kwargs["name"], kwargs["mac_addr"])
        (hvac_modes := list(DEFAULT_HVAC_MODES)).extend(kwargs.get("hvac_modes", []))
        _LOGGER.info(f"Initialize the device {self._name}...")
        self._hvac_modes_enabled = _sort_by_list(hvac_modes, HVAC_MODES)
        self._fan_modes_enabled = _sort_by_list(kwargs.get("fan_modes"), FAN_MODES)
        GreeClimateBase.__init__(
            self,
            hass, 
            self._name, 
            kwargs["host"], 
            kwargs["port"], 
            kwargs["mac_addr"].encode().replace(b':', b''), 
            kwargs["timeout"], 
            kwargs["temp_step"], 
            kwargs.get("temp_sensor", ""), 
            "", 
            "", 
            "", 
            "", 
            "", 
            "", 
            "", 
            HVAC_MODES, 
            FAN_MODES, 
            SWING_MODES, 
            kwargs.get("encryption_key", None), 
            kwargs.get("uid", None)
        )
        self.entity_id = self._entity_common_perfix

    @property
    def name(self):
        return "空调"
    
    @property
    def hvac_modes(self):
        _LOGGER.info('hvac_modes(): ' + str(self._hvac_modes_enabled))
        return self._hvac_modes_enabled

    @property
    def fan_modes(self):
        _LOGGER.info('fan_list(): ' + str(self._fan_modes_enabled))
        return self._fan_modes_enabled
    
    @property
    def swing_modes(self):
        return SWING_MODES
    
    def UpdateHACurrentSwingMode(self):
        ud = 1 if self._acOptions['SwUpDn'] == 1 else 0
        lr = 2 if self._acOptions['SwingLfRig'] == 1 else 0
        self._swing_mode = self._swing_modes[ud + lr]
        _LOGGER.info('HA swing mode set according to HVAC state to: ' + str(self._swing_mode))
    
    def set_swing_mode(self, swing_mode):
        _LOGGER.info('Set swing mode(): ' + str(swing_mode))
        if not (self._acOptions['Pow'] == 0):
            _LOGGER.info('SyncState with Swing=' + str(swing_mode))
            self.SyncState({
                'SwUpDn': 1 if swing_mode in (SWING_BOTH, SWING_VERTICAL) else 0, 
                'SwingLfRig': 1 if swing_mode in (SWING_BOTH, SWING_HORIZONTAL) else 0
            })
            self.schedule_update_ha_state()
