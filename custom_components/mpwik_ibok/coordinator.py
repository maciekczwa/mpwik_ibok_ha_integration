"""Data coordinator for MPWIK iBOK integration."""
import logging
from datetime import timedelta
from typing import Optional

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(hours=24)


class MPWIKIBOKCoordinator(DataUpdateCoordinator):
    """Coordinator to manage MPWIK iBOK API calls."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="MPWIK iBOK",
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry

    async def _async_update_data(self) -> dict:
        """Fetch data from MPWIK iBOK API."""
        username = self.entry.data.get("username")
        password = self.entry.data.get("password")
        server_url = self.entry.data.get("server_url")
        
        # Ensure server_url has trailing slash
        if server_url and not server_url.endswith("/"):
            server_url = server_url + "/"

        _LOGGER.debug("Fetching data from %s", server_url)

        async with aiohttp.ClientSession() as session:
            # Login
            login_data = {
                "user": username.lower().strip(),
                "pass": password,
            }

            _LOGGER.debug("Attempting login...")
            try:
                async with session.post(
                    f"{server_url}api/?method=login",
                    data=login_data,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        _LOGGER.error("Login failed with status %d", resp.status)
                        raise UpdateFailed(f"Login failed with status {resp.status}")

                    login_response = await resp.json()
                    _LOGGER.debug("Login response: %s", login_response)

                    if login_response.get("status") != "ok":
                        error_status = login_response.get("status")
                        
                        # Handle session limit error
                        if error_status == "sessionLimit":
                            _LOGGER.warning("Session limit reached, logging out all sessions...")
                            
                            # Get any valid sid from previous attempt if available
                            # Try logout all with empty/dummy sid first
                            try:
                                async with session.get(
                                    f"{server_url}api/?method=logoutAll",
                                    ssl=False,
                                    timeout=aiohttp.ClientTimeout(total=30),
                                ) as logout_resp:
                                    logout_response = await logout_resp.json()
                                    _LOGGER.debug("LogoutAll response: %s", logout_response)
                            except Exception as e:
                                _LOGGER.warning("LogoutAll error: %s", e)
                            
                            # Retry login after logout
                            _LOGGER.debug("Retrying login after logoutAll...")
                            try:
                                async with session.post(
                                    f"{server_url}api/?method=login",
                                    data=login_data,
                                    ssl=False,
                                    timeout=aiohttp.ClientTimeout(total=30),
                                ) as retry_resp:
                                    if retry_resp.status != 200:
                                        _LOGGER.error("Retry login failed with status %d", retry_resp.status)
                                        raise UpdateFailed(f"Login failed after session logout")
                                    
                                    retry_response = await retry_resp.json()
                                    _LOGGER.debug("Retry login response: %s", retry_response)
                                    
                                    if retry_response.get("status") != "ok":
                                        _LOGGER.error("Retry login error: %s", retry_response.get("status"))
                                        raise UpdateFailed(f"Login error after session logout: {retry_response.get('status')}")
                                    
                                    login_response = retry_response
                            except aiohttp.ClientError as e:
                                _LOGGER.error("Retry login connection error: %s", e)
                                raise UpdateFailed(f"Login connection error after logout: {e}")
                        else:
                            _LOGGER.error("Login error: %s", error_status)
                            raise UpdateFailed(f"Login error: {error_status}")

                    sid = login_response.get("sid")
                    if not sid:
                        _LOGGER.error("No session ID in login response")
                        raise UpdateFailed("No session ID in login response")

                    _LOGGER.debug("Login successful, SID: %s", sid)
            except aiohttp.ClientError as e:
                _LOGGER.error("Login connection error: %s", e)
                raise UpdateFailed(f"Login connection error: {e}")

            # Fetch balance
            headers = {"Cookie": f"PHPSESSID={sid}"}

            balance = None
            _LOGGER.debug("Fetching balance...")
            try:
                async with session.get(
                    f"{server_url}api/?method=balance",
                    headers=headers,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        balance_response = await resp.json()
                        _LOGGER.debug("Balance response: %s", balance_response)
                        balance = float(balance_response.get("balance", 0)) if balance_response.get("balance") else None
                        _LOGGER.debug("Balance: %s", balance)
                    else:
                        _LOGGER.warning("Failed to fetch balance: status %d", resp.status)
            except Exception as e:
                _LOGGER.warning("Error fetching balance: %s", e)

            # Fetch invoices
            last_invoice = None
            _LOGGER.debug("Fetching invoices...")
            try:
                async with session.get(
                    f"{server_url}api/?method=invoice",
                    headers=headers,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        invoices = await resp.json()
                        _LOGGER.debug("Invoices response: %s", invoices)
                        if invoices and len(invoices) > 0:
                            inv = invoices[0]
                            last_invoice = {
                                "invoice_number": inv.get("nd", "N/A"),
                                "due_date": inv.get("pd", "N/A"),
                                "amount_owed": float(inv.get("owe", 0)),
                                "gross_amount": float(inv.get("brutto", 0)),
                                "net_amount": float(inv.get("netto", 0)),
                                "vat": float(inv.get("vat", 0)),
                            }
                            _LOGGER.debug("Last invoice: %s", last_invoice)
                    else:
                        _LOGGER.warning("Failed to fetch invoices: status %d", resp.status)
            except Exception as e:
                _LOGGER.warning("Error fetching invoices: %s", e)

            # Fetch meter readout list
            meter_state = None
            readout_date = None
            consumption = None
            _LOGGER.debug("Fetching meter readout list...")
            try:
                async with session.get(
                    f"{server_url}api/?method=readoutlist",
                    headers=headers,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        meter_points = await resp.json()
                        _LOGGER.debug("Meter points response: %s", meter_points)
                        if isinstance(meter_points, list) and len(meter_points) > 0:
                            meter_point = meter_points[0]
                            readouts = meter_point.get("readouts", [])
                            if readouts and len(readouts) > 0:
                                last_readout = readouts[0]
                                meter_state = last_readout.get("readoutvalue", None)
                                readout_date = last_readout.get("readoutdate", None)
                                consumption = last_readout.get("consumption", None)
                                _LOGGER.debug(
                                    "Meter state: %s, Date: %s, Consumption: %s",
                                    meter_state,
                                    readout_date,
                                    consumption,
                                )
                    else:
                        _LOGGER.warning("Failed to fetch meter readout: status %d", resp.status)
            except Exception as e:
                _LOGGER.warning("Error fetching meter readout: %s", e)

            # Logout
            _LOGGER.debug("Logging out...")
            try:
                async with session.get(
                    f"{server_url}api/?method=logout",
                    headers=headers,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    _LOGGER.debug("Logout status: %d", resp.status)
            except Exception as err:
                _LOGGER.warning("Logout error: %s", err)

            data = {
                "balance": balance,
                "last_invoice": last_invoice,
                "meter_state": meter_state,
                "readout_date": readout_date,
                "consumption": consumption,
            }
            
            _LOGGER.debug("Returning data: %s", data)
            return data
