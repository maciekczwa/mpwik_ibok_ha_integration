"""MPWIK iBOK integration for Home Assistant."""
import asyncio
import logging
from datetime import timedelta
from typing import Final

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

DOMAIN: Final = "mpwik_ibok"
PLATFORMS: Final = [Platform.SENSOR]
SCAN_INTERVAL = timedelta(hours=24)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MPWIK iBOK from a config entry."""
    
    coordinator = IBOKDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


class IBOKDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to manage MPWIK iBOK data updates."""
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        
        self.entry = entry
        self.data = {
            "balance": 0,
            "last_invoice": None,
            "error": None
        }
    
    async def _async_update_data(self):
        """Fetch data from MPWIK iBOK API."""
        try:
            username = self.entry.data.get("username")
            password = self.entry.data.get("password")
            server_url = self.entry.data.get("server_url")
            
            async with aiohttp.ClientSession() as session:
                # Login
                login_data = {
                    "user": username.lower().strip(),
                    "pass": password
                }
                
                async with session.post(
                    f"{server_url}/api/?method=login",
                    data=login_data,
                    ssl=False
                ) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"Login failed with status {resp.status}")
                    
                    login_response = await resp.json()
                    
                    if login_response.get("status") != "ok":
                        raise UpdateFailed(f"Login error: {login_response.get('status')}")
                    
                    sid = login_response.get("sid")
                    if not sid:
                        raise UpdateFailed("No session ID in login response")
                
                # Fetch balance
                headers = {"Cookie": f"PHPSESSID={sid}"}
                
                async with session.get(
                    f"{server_url}/api/?method=balance",
                    headers=headers,
                    ssl=False
                ) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"Failed to fetch balance: {resp.status}")
                    
                    balance_response = await resp.json()
                    balance = balance_response.get("balance", 0)
                
                # Fetch invoices
                async with session.get(
                    f"{server_url}/api/?method=invoice",
                    headers=headers,
                    ssl=False
                ) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"Failed to fetch invoices: {resp.status}")
                    
                    invoices = await resp.json()
                
                # Logout
                async with session.get(
                    f"{server_url}/api/?method=logout",
                    headers=headers,
                    ssl=False
                ) as resp:
                    pass  # Ignore logout response
                
                # Process data
                last_invoice = None
                if invoices and len(invoices) > 0:
                    inv = invoices[0]
                    last_invoice = {
                        "invoice_number": inv.get("nd", "N/A"),
                        "due_date": inv.get("pd", "N/A"),
                        "amount_owed": inv.get("owe", "0"),
                        "gross_amount": inv.get("brutto", "0"),
                        "net_amount": inv.get("netto", "0"),
                        "vat": inv.get("vat", "0")
                    }
                
                return {
                    "balance": float(balance),
                    "last_invoice": last_invoice,
                    "error": None
                }
        
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout connecting to MPWIK iBOK: {err}") from err
        except Exception as err:
            _LOGGER.error("Error updating MPWIK iBOK data: %s", err)
            raise UpdateFailed(f"Error updating MPWIK iBOK data: {err}") from err
