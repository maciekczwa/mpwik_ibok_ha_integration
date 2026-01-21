"""Config flow for MPWIK iBOK integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)

DOMAIN = "mpwik_ibok"


class MPWIKIBOKConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MPWIK iBOK."""
    
    VERSION = 1
    
    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            # Validate input
            try:
                await self._validate_input(user_input)
            except Exception as err:
                _LOGGER.error("Error validating input: %s", err)
                error_msg = str(err)
                
                # Map errors to user-friendly messages
                if "HTML instead of JSON" in error_msg:
                    errors["base"] = "invalid_server_url"
                elif "Invalid credentials" in error_msg:
                    errors["base"] = "invalid_auth"
                elif "Connection error" in error_msg:
                    errors["base"] = "cannot_connect"
                else:
                    errors["base"] = "invalid_auth"
            
            if not errors:
                return self.async_create_entry(
                    title=user_input["username"],
                    data=user_input,
                )
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Required("server_url", description="https://ibok.mpwik.bedzin.pl"): str,
                }
            ),
            errors=errors,
            description_placeholders={},
        )
    
    async def _validate_input(self, user_input: Dict[str, Any]) -> None:
        """Validate the user input allows us to connect."""
        import aiohttp
        from urllib.parse import urljoin
        
        username = user_input.get("username")
        password = user_input.get("password")
        server_url = user_input.get("server_url").strip()
        
        # Ensure server_url ends with / for proper urljoin
        if not server_url.endswith("/"):
            server_url = server_url + "/"
        
        # Store normalized URL
        user_input["server_url"] = server_url
        
        _LOGGER.debug("Validating with server_url: %s", server_url)
        
        async with aiohttp.ClientSession() as session:
            login_data = {
                "user": username.lower().strip(),
                "pass": password
            }
            
            login_url = urljoin(server_url, "api/?method=login")
            _LOGGER.debug("Login URL: %s", login_url)
            
            try:
                async with session.post(
                    login_url,
                    data=login_data,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    _LOGGER.debug("Login response status: %d", resp.status)
                    _LOGGER.debug("Login response content-type: %s", resp.content_type)
                    
                    if resp.status != 200:
                        _LOGGER.error("Login failed with status %d", resp.status)
                        raise Exception(f"Login failed with status {resp.status}")
                    
                    # Check content type before trying to parse JSON
                    if "application/json" not in resp.content_type:
                        _LOGGER.error("Unexpected response content-type: %s", resp.content_type)
                        text = await resp.text()
                        _LOGGER.error("Response body: %s", text[:500])
                        raise Exception(f"Server returned HTML instead of JSON. Check server URL and credentials.")
                    
                    try:
                        login_response = await resp.json()
                    except Exception as e:
                        _LOGGER.error("Failed to parse JSON response: %s", e)
                        raise Exception("Server response is not valid JSON")
                    
                    _LOGGER.debug("Login response: %s", login_response)
                    
                    if login_response.get("status") != "ok":
                        _LOGGER.error("Invalid credentials or server error: %s", login_response.get("status"))
                        raise Exception(f"Invalid credentials or server error")
                    
                    sid = login_response.get("sid")
                    if not sid:
                        _LOGGER.error("No session ID in login response")
                        raise Exception("No session ID in login response")
                    
                    _LOGGER.debug("Login successful, SID: %s", sid)
                    
                    # Logout
                    headers = {"Cookie": f"PHPSESSID={sid}"}
                    logout_url = urljoin(server_url, "api/?method=logout")
                    try:
                        async with session.get(
                            logout_url,
                            headers=headers,
                            ssl=False,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as logout_resp:
                            _LOGGER.debug("Logout status: %d", logout_resp.status)
                    except Exception as e:
                        _LOGGER.warning("Logout error: %s", e)
                        
            except aiohttp.ClientError as e:
                _LOGGER.error("Connection error: %s", e)
                raise Exception(f"Connection error: {e}")
            except Exception as e:
                _LOGGER.error("Validation error: %s", e)
                raise
