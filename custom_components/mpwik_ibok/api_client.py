"""MPWIK iBOK API Client - Standalone module for API interactions."""
import logging
import json
from typing import Optional, Dict, Any, List
import aiohttp

_LOGGER = logging.getLogger(__name__)


class MPWIKIBOKApiError(Exception):
    """Exception for API errors."""
    pass


class MPWIKIBOKAuthError(MPWIKIBOKApiError):
    """Exception for authentication errors."""
    pass


class MPWIKIBOKConnectionError(MPWIKIBOKApiError):
    """Exception for connection errors."""
    pass


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
            raise MPWIKIBOKApiError("Empty response")
        except json.JSONDecodeError as e:
            _LOGGER.error("Failed to parse response as JSON: %s", e)
            _LOGGER.debug("Response text: %s", text[:500] if text else "")
            raise MPWIKIBOKApiError(f"Invalid JSON response: {e}")


class MPWIKIBOKApiClient:
    """Client for MPWIK iBOK API."""

    def __init__(
        self,
        server_url: str,
        username: str,
        password: str,
        timeout: int = 30,
    ):
        """Initialize the API client.
        
        Args:
            server_url: The base URL of the MPWIK iBOK server
            username: Username for authentication
            password: Password for authentication
            timeout: Timeout in seconds for API requests (default: 30)
        """
        self.server_url = server_url if server_url.endswith("/") else server_url + "/"
        self.username = username
        self.password = password
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self._sid: Optional[str] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.logout()

    async def login(self, session: Optional[aiohttp.ClientSession] = None) -> str:
        """Login to MPWIK iBOK API.
        
        Args:
            session: Optional existing aiohttp session to use
            
        Returns:
            Session ID (sid)
            
        Raises:
            MPWIKIBOKAuthError: If authentication fails
            MPWIKIBOKConnectionError: If connection fails
        """
        use_existing_session = session is not None
        if not use_existing_session:
            session = aiohttp.ClientSession()
            self._session = session

        login_data = {
            "user": self.username,
            "pass": self.password,
        }

        _LOGGER.debug("Attempting login to %s", self.server_url)
        try:
            async with session.post(
                f"{self.server_url}api/?method=login",
                data=login_data,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    _LOGGER.error("Login failed with status %d. Response: %s", resp.status, text)
                    raise MPWIKIBOKAuthError(f"Login failed with status {resp.status}")

                login_response = await parse_json_response(resp)
                _LOGGER.debug("Login response: %s", login_response)

                if login_response.get("status") != "ok":
                    error_status = login_response.get("status")
                    error_msg = login_response.get("message", "Unknown error")
                    
                    # Handle session limit error
                    if login_response.get("sessionLimit"):
                        _LOGGER.warning("Session limit reached, logging out all sessions...")
                        
                        await self._logout_all(session)
                        
                        # Retry login after logout
                        _LOGGER.debug("Retrying login after logoutAll...")
                        async with session.post(
                            f"{self.server_url}api/?method=login",
                            data=login_data,
                            ssl=False,
                            timeout=aiohttp.ClientTimeout(total=self.timeout),
                        ) as retry_resp:
                            if retry_resp.status != 200:
                                text = await retry_resp.text()
                                _LOGGER.error("Retry login failed with status %d. Response: %s", retry_resp.status, text)
                                raise MPWIKIBOKAuthError("Login failed after session logout")
                            
                            retry_response = await parse_json_response(retry_resp)
                            _LOGGER.debug("Retry login response: %s", retry_response)
                            
                            if retry_response.get("status") != "ok":
                                retry_error = retry_response.get("status")
                                retry_msg = retry_response.get("message", "Unknown error")
                                _LOGGER.error("Retry login error: %s - %s", retry_error, retry_msg)
                                raise MPWIKIBOKAuthError(f"Login error after session logout: {retry_error}")
                            
                            login_response = retry_response
                    else:
                        _LOGGER.error("Login error: %s - %s", error_status, error_msg)
                        raise MPWIKIBOKAuthError(f"Login error: {error_status} - {error_msg}")

                sid = login_response.get("sid")
                if not sid:
                    _LOGGER.error("No session ID in login response")
                    raise MPWIKIBOKAuthError("No session ID in login response")

                _LOGGER.debug("Login successful, SID: %s", sid)
                self._sid = sid
                return sid
                
        except aiohttp.ClientError as e:
            _LOGGER.error("Login connection error: %s", e)
            if not use_existing_session and self._session:
                await self._session.close()
                self._session = None
            raise MPWIKIBOKConnectionError(f"Login connection error: {e}")

    async def _logout_all(self, session: aiohttp.ClientSession) -> None:
        """Logout all sessions for the user.
        
        Args:
            session: aiohttp session to use
        """
        logout_url = f"{self.server_url}api/?method=logoutall"
        _LOGGER.debug("LogoutAll URL: %s", logout_url)
        logout_data = {
            "user": self.username,
            "pass": self.password,
        }
        try:
            async with session.post(
                logout_url,
                data=logout_data,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as logout_resp:
                _LOGGER.debug("LogoutAll response status: %d", logout_resp.status)
                try:
                    logout_response = await parse_json_response(logout_resp)
                    _LOGGER.debug("LogoutAll response: %s", logout_response)
                except MPWIKIBOKApiError as e:
                    _LOGGER.warning("Failed to parse logoutAll response: %s", e)
        except Exception as e:
            _LOGGER.warning("LogoutAll error: %s", e)

    async def logout(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        """Logout from MPWIK iBOK API.
        
        Args:
            session: Optional existing aiohttp session to use
        """
        if not self._sid:
            _LOGGER.debug("No active session to logout")
            return

        use_existing_session = session is not None
        session = session or self._session
        
        if not session:
            _LOGGER.warning("No session available for logout")
            self._sid = None
            return

        headers = {"Cookie": f"PHPSESSID={self._sid}"}
        _LOGGER.debug("Logging out...")
        try:
            async with session.get(
                f"{self.server_url}api/?method=logout",
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
        finally:
            self._sid = None
            if not use_existing_session and self._session:
                await self._session.close()
                self._session = None

    async def get_balance(self, session: Optional[aiohttp.ClientSession] = None) -> Optional[float]:
        """Get account balance.
        
        Args:
            session: Optional existing aiohttp session to use
            
        Returns:
            Balance as float, or None if unavailable
            
        Raises:
            MPWIKIBOKAuthError: If not logged in
            MPWIKIBOKApiError: If API request fails
        """
        if not self._sid:
            raise MPWIKIBOKAuthError("Not logged in")

        session = session or self._session
        if not session:
            raise MPWIKIBOKApiError("No session available")

        headers = {"Cookie": f"PHPSESSID={self._sid}"}
        _LOGGER.debug("Fetching balance...")
        
        try:
            async with session.get(
                f"{self.server_url}api/?method=balance",
                headers=headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status == 200:
                    balance_response = await parse_json_response(resp)
                    _LOGGER.debug("Balance response: %s", balance_response)
                    balance = float(balance_response.get("balance", 0)) if balance_response.get("balance") else None
                    _LOGGER.debug("Balance: %s", balance)
                    return balance
                else:
                    text = await resp.text()
                    _LOGGER.error("Failed to fetch balance: status %d. Response: %s", resp.status, text)
                    raise MPWIKIBOKApiError(f"Failed to fetch balance: status {resp.status}")
        except MPWIKIBOKApiError:
            raise
        except Exception as e:
            _LOGGER.error("Error fetching balance: %s", e)
            raise MPWIKIBOKApiError(f"Error fetching balance: {e}")

    async def get_invoices(self, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        """Get list of invoices.
        
        Args:
            session: Optional existing aiohttp session to use
            
        Returns:
            List of invoice dictionaries
            
        Raises:
            MPWIKIBOKAuthError: If not logged in
            MPWIKIBOKApiError: If API request fails
        """
        if not self._sid:
            raise MPWIKIBOKAuthError("Not logged in")

        session = session or self._session
        if not session:
            raise MPWIKIBOKApiError("No session available")

        headers = {"Cookie": f"PHPSESSID={self._sid}"}
        _LOGGER.debug("Fetching invoices...")
        
        try:
            async with session.get(
                f"{self.server_url}api/?method=invoice",
                headers=headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status == 200:
                    invoices = await parse_json_response(resp)
                    _LOGGER.debug("Invoices response: %s", invoices)
                    
                    # Parse invoices into a normalized format
                    parsed_invoices = []
                    if invoices and isinstance(invoices, list):
                        for inv in invoices:
                            parsed_invoices.append({
                                "invoice_number": inv.get("nd", "N/A"),
                                "due_date": inv.get("pd", "N/A"),
                                "amount_owed": float(inv.get("owe", 0)),
                                "gross_amount": float(inv.get("brutto", 0)),
                                "net_amount": float(inv.get("netto", 0)),
                                "vat": float(inv.get("vat", 0)),
                            })
                    
                    _LOGGER.debug("Parsed %d invoices", len(parsed_invoices))
                    return parsed_invoices
                else:
                    text = await resp.text()
                    _LOGGER.error("Failed to fetch invoices: status %d. Response: %s", resp.status, text)
                    raise MPWIKIBOKApiError(f"Failed to fetch invoices: status {resp.status}")
        except MPWIKIBOKApiError:
            raise
        except Exception as e:
            _LOGGER.error("Error fetching invoices: %s", e)
            raise MPWIKIBOKApiError(f"Error fetching invoices: {e}")

    async def get_meter_readouts(self, session: Optional[aiohttp.ClientSession] = None) -> Dict[str, Any]:
        """Get meter readout information.
        
        Args:
            session: Optional existing aiohttp session to use
            
        Returns:
            Dictionary with meter state, readout date, and consumption
            
        Raises:
            MPWIKIBOKAuthError: If not logged in
            MPWIKIBOKApiError: If API request fails
        """
        if not self._sid:
            raise MPWIKIBOKAuthError("Not logged in")

        session = session or self._session
        if not session:
            raise MPWIKIBOKApiError("No session available")

        headers = {"Cookie": f"PHPSESSID={self._sid}"}
        _LOGGER.debug("Fetching meter readout list...")
        
        try:
            async with session.get(
                f"{self.server_url}api/?method=readoutlist",
                headers=headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status == 200:
                    meter_points = await parse_json_response(resp)
                    _LOGGER.debug("Meter points response: %s", meter_points)
                    
                    meter_state = None
                    readout_date = None
                    consumption = None
                    
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
                    
                    return {
                        "meter_state": meter_state,
                        "readout_date": readout_date,
                        "consumption": consumption,
                    }
                else:
                    text = await resp.text()
                    _LOGGER.error("Failed to fetch meter readout: status %d. Response: %s", resp.status, text)
                    raise MPWIKIBOKApiError(f"Failed to fetch meter readout: status {resp.status}")
        except MPWIKIBOKApiError:
            raise
        except Exception as e:
            _LOGGER.error("Error fetching meter readout: %s", e)
            raise MPWIKIBOKApiError(f"Error fetching meter readout: {e}")

    async def get_all_data(self) -> Dict[str, Any]:
        """Fetch all data (balance, invoices, meter readouts) in one session.
        
        Returns:
            Dictionary with all data
            
        Raises:
            MPWIKIBOKAuthError: If authentication fails
            MPWIKIBOKConnectionError: If connection fails
            MPWIKIBOKApiError: If API request fails
        """
        async with aiohttp.ClientSession() as session:
            # Login
            await self.login(session)
            
            try:
                # Fetch all data
                balance = None
                try:
                    balance = await self.get_balance(session)
                except Exception as e:
                    _LOGGER.error("Failed to get balance: %s", e)
                
                invoices = []
                try:
                    invoices = await self.get_invoices(session)
                except Exception as e:
                    _LOGGER.error("Failed to get invoices: %s", e)
                
                meter_data = {}
                try:
                    meter_data = await self.get_meter_readouts(session)
                except Exception as e:
                    _LOGGER.error("Failed to get meter readouts: %s", e)
                
                # Get last invoice
                last_invoice = invoices[0] if invoices else None
                
                return {
                    "balance": balance,
                    "last_invoice": last_invoice,
                    "meter_state": meter_data.get("meter_state"),
                    "readout_date": meter_data.get("readout_date"),
                    "consumption": meter_data.get("consumption"),
                }
            finally:
                # Logout
                await self.logout(session)
