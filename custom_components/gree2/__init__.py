from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

DOMAIN = "gree2"

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SWITCH
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Triggered by config entry options updates."""
    await hass.config_entries.async_reload(entry.entry_id)


class DeviceBase:

    def __init__(self, name: str, mac_addr: str) -> None:
        self._name = name
        self._mac_addr = mac_addr.replace(":", "").lower()
        if not name:
            self._name = "Gree_" + self._mac_addr
        self._entity_common_perfix = DOMAIN + ".gree_" + self._mac_addr

    @property
    def device_info(self) -> DeviceInfo:
        """Device info"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac_addr)},
            name=self._name,
            manufacturer="Gree",
            model=self._mac_addr
        )
    
    @property
    def has_entity_name(self) -> bool:
        return True