"""MPWIK iBOK integration for Home Assistant."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from .coordinator import MPWIKIBOKCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "mpwik_ibok"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MPWIK iBOK from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Create coordinator for this entry
    coordinator = MPWIKIBOKCoordinator(hass, entry)
    
    # Perform first refresh
    await coordinator.async_config_entry_first_refresh()
    
    # Store coordinator in hass.data
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
