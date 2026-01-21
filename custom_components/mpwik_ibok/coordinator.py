"""Data coordinator for MPWIK iBOK integration."""
import logging
from datetime import timedelta
from typing import Optional
import json

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(hours=24)
# Exponential backoff: 5min, 15min, 1h, 3h (max)
RETRY_BACKOFF_TIMES = [300, 900, 3600, 10800]


async def parse_json_response(resp: aiohttp.ClientResponse) -> dict:
    """Parse JSON response ignoring content-type header."""
    try:
        # First try the normal way
        return await resp.json()
    except (json.JSONDecodeError, ValueError, aiohttp.ContentTypeError):
        # If that fails, try parsing text as JSON anyway
        try:
            text = await resp.text()
            if text:
                return json.loads(text)
            raise UpdateFailed("Empty response")
        except json.JSONDecodeError as e:
            _LOGGER.error("Failed to parse response as JSON: %s", e)
            _LOGGER.debug("Response text: %s", text[:500] if text else "")
            raise UpdateFailed(f"Invalid JSON response: {e}")


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
        self.last_update_error_time: Optional[float] = None
        self.error_count = 0

    async def _async_update_data(self) -> dict:
        """Fetch data from MPWIK iBOK API."""
        import time
        
        # Check if we should skip due to backoff
        if self.last_update_error_time is not None and self.error_count > 0:
            backoff_index = min(self.error_count - 1, len(RETRY_BACKOFF_TIMES) - 1)
            backoff_delay = RETRY_BACKOFF_TIMES[backoff_index]
            time_since_error = time.time() - self.last_update_error_time
            
            if time_since_error < backoff_delay:
                remaining = backoff_delay - time_since_error
                _LOGGER.warning(
                    "Skipping update due to backoff (error %d). Retry in %.0f seconds",
                    self.error_count,
                    remaining
                )
                raise UpdateFailed(f"Backoff active, retry in {remaining:.0f}s")
        
        username = self.entry.data.get("username")
        password = self.entry.data.get("password")
        server_url = self.entry.data.get("server_url")
        
        # Ensure server_url has trailing slash
        if server_url and not server_url.endswith("/"):
            server_url = server_url + "/"

        _LOGGER.debug("Fetching data from %s", server_url)

        try:
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
                            text = await resp.text()
                            _LOGGER.error("Login failed with status %d. Response: %s", resp.status, text)
                            raise UpdateFailed(f"Login failed with status {resp.status}")

                        login_response = await parse_json_response(resp)
                        _LOGGER.debug("Login response: %s", login_response)

                        if login_response.get("status") != "ok":
                            error_status = login_response.get("status")
                            error_msg = login_response.get("message", "Unknown error")
                            
                            # Handle session limit error
                            if error_status == "sessionLimit":
                                _LOGGER.warning("Session limit reached, logging out all sessions...")
                                
                                try:
                                    async with session.get(
                                        f"{server_url}api/?method=logoutAll",
                                        ssl=False,
                                        timeout=aiohttp.ClientTimeout(total=30),
                                    ) as logout_resp:
                                        try:
                                            logout_response = await parse_json_response(logout_resp)
                                            _LOGGER.debug("LogoutAll response: %s", logout_response)
                                        except UpdateFailed as e:
                                            _LOGGER.warning("Failed to parse logoutAll response: %s", e)
                                            # Continue with retry anyway
                                except Exception as e:
                                    _LOGGER.warning("LogoutAll error: %s", e)
                                    # Continue with retry anyway
                                
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
                                            text = await retry_resp.text()
                                            _LOGGER.error("Retry login failed with status %d. Response: %s", retry_resp.status, text)
                                            raise UpdateFailed(f"Login failed after session logout")
                                        
                                        retry_response = await parse_json_response(retry_resp)
                                        _LOGGER.debug("Retry login response: %s", retry_response)
                                        
                                        if retry_response.get("status") != "ok":
                                            retry_error = retry_response.get("status")
                                            retry_msg = retry_response.get("message", "Unknown error")
                                            _LOGGER.error("Retry login error: %s - %s", retry_error, retry_msg)
                                            raise UpdateFailed(f"Login error after session logout: {retry_error}")
                                        
                                        login_response = retry_response
                                except aiohttp.ClientError as e:
                                    _LOGGER.error("Retry login connection error: %s", e)
                                    raise UpdateFailed(f"Login connection error after logout: {e}")
                                except UpdateFailed:
                                    raise
                                except Exception as e:
                                    _LOGGER.error("Retry login error: %s", e)
                                    raise UpdateFailed(f"Login retry failed: {e}")
                            else:
                                _LOGGER.error("Login error: %s - %s", error_status, error_msg)
                                raise UpdateFailed(f"Login error: {error_status} - {error_msg}")

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
                            balance_response = await parse_json_response(resp)
                            _LOGGER.debug("Balance response: %s", balance_response)
                            balance = float(balance_response.get("balance", 0)) if balance_response.get("balance") else None
                            _LOGGER.debug("Balance: %s", balance)
                        else:
                            text = await resp.text()
                            _LOGGER.error("Failed to fetch balance: status %d. Response: %s", resp.status, text)
                except Exception as e:
                    _LOGGER.error("Error fetching balance: %s", e)

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
                            invoices = await parse_json_response(resp)
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
                            text = await resp.text()
                            _LOGGER.error("Failed to fetch invoices: status %d. Response: %s", resp.status, text)
                except Exception as e:
                    _LOGGER.error("Error fetching invoices: %s", e)

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
                            meter_points = await parse_json_response(resp)
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
                            text = await resp.text()
                            _LOGGER.error("Failed to fetch meter readout: status %d. Response: %s", resp.status, text)
                except Exception as e:
                    _LOGGER.error("Error fetching meter readout: %s", e)

                # Logout
                _LOGGER.debug("Logging out...")
                try:
                    async with session.get(
                        f"{server_url}api/?method=logout",
                        headers=headers,
                        ssl=False,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            _LOGGER.debug("Logout successful")
                        else:
                            text = await resp.text()
                            _LOGGER.debug("Logout failed with status %d. Response: %s", resp.status, text)
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
                
                # Reset error tracking on successful update
                self.error_count = 0
                self.last_update_error_time = None
                
                return data
        
        except UpdateFailed as e:
            # Track error for backoff
            import time
            self.last_update_error_time = time.time()
            self.error_count += 1
            backoff_index = min(self.error_count - 1, len(RETRY_BACKOFF_TIMES) - 1)
            backoff_delay = RETRY_BACKOFF_TIMES[backoff_index]
            _LOGGER.error(
                "Update failed (attempt %d). Next retry in %d seconds: %s",
                self.error_count,
                backoff_delay,
                str(e)
            )
            raise
        except Exception as e:
            # Track error for backoff
            import time
            self.last_update_error_time = time.time()
            self.error_count += 1
            backoff_index = min(self.error_count - 1, len(RETRY_BACKOFF_TIMES) - 1)
            backoff_delay = RETRY_BACKOFF_TIMES[backoff_index]
            _LOGGER.error(
                "Update failed with exception (attempt %d). Next retry in %d seconds: %s",
                self.error_count,
                backoff_delay,
                str(e),
                exc_info=True
            )
            raise UpdateFailed(f"Update failed: {e}") from e
            import time
            self.last_update_error_time = time.time()
            self.error_count += 1
            backoff_index = min(self.error_count - 1, len(RETRY_BACKOFF_TIMES) - 1)
            backoff_delay = RETRY_BACKOFF_TIMES[backoff_index]
            _LOGGER.error(
                "Unexpected error (attempt %d). Next retry in %d seconds: %s",
                self.error_count,
                backoff_delay,
                e
            )
            raise UpdateFailed(f"Unexpected error: {e}")
