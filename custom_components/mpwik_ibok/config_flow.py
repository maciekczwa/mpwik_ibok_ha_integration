"""Config flow for MPWIK iBOK integration."""
import logging
from typing import Any, Dict, Optional
import json

import voluptuous as vol
import aiohttp
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)

DOMAIN = "mpwik_ibok"


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
            raise ValueError("Empty response")
        except json.JSONDecodeError as e:
            _LOGGER.error("Failed to parse response as JSON: %s", e)
            _LOGGER.debug("Response text: %s", text[:500] if text else "")
            raise ValueError(f"Invalid JSON response: {e}")


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
                if "Invalid credentials" in error_msg or "Invalid auth" in error_msg:
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
        
        # Ensure server_url ends with / for proper URL construction
        if not server_url.endswith("/"):
            server_url = server_url + "/"
        
        # Store normalized URL
        user_input["server_url"] = server_url
        
        _LOGGER.debug("Validating with server_url: %s", server_url)
        
        async with aiohttp.ClientSession() as session:
            login_data = {
                "user": username,
                "pass": password
            }
            
            login_url = f"{server_url}api/?method=login"
            _LOGGER.debug("Login URL: %s", login_url)
            
            try:
                async with session.post(
                    login_url,
                    data=login_data,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    _LOGGER.debug("Login response status: %d", resp.status)
                    
                    if resp.status != 200:
                        _LOGGER.error("Login failed with status %d", resp.status)
                        raise Exception(f"Login failed with status {resp.status}")
                    
                    login_response = await parse_json_response(resp)
                    _LOGGER.debug("Login response: %s", login_response)
                    
                    if login_response.get("status") != "ok":
                        error_status = login_response.get("status")
                        
                        # Handle session limit during validation
                        if login_response.get("sessionLimit"):
                            _LOGGER.warning("Session limit reached during validation, logging out all sessions...")
                            
                            logout_url = f"{server_url}api/?method=logoutall"
                            _LOGGER.debug("LogoutAll URL: %s", logout_url)
                            logout_data = {
                                "user": username,
                                "pass": password,
                            }
                            try:
                                async with session.post(
                                    logout_url,
                                    data=logout_data,
                                    ssl=False,
                                    timeout=aiohttp.ClientTimeout(total=10)
                                ) as logout_resp:
                                    _LOGGER.debug("LogoutAll response status: %d", logout_resp.status)
                                    try:
                                        logout_response = await parse_json_response(logout_resp)
                                        _LOGGER.debug("LogoutAll response: %s", logout_response)
                                    except Exception as e:
                                        _LOGGER.warning("Failed to parse logoutAll response: %s", e)
                                        # Still continue with retry even if logoutAll response parsing fails
                            except Exception as e:
                                _LOGGER.warning("LogoutAll error: %s", e)
                                # Still continue with retry even if logoutAll fails
                            
                            # Retry login
                            _LOGGER.debug("Retrying login after logoutAll...")
                            try:
                                async with session.post(
                                    login_url,
                                    data=login_data,
                                    ssl=False,
                                    timeout=aiohttp.ClientTimeout(total=10)
                                ) as retry_resp:
                                    if retry_resp.status != 200:
                                        _LOGGER.error("Retry login failed with status %d", retry_resp.status)
                                        raise Exception("Login failed after session logout")
                                    
                                    try:
                                        retry_response = await parse_json_response(retry_resp)
                                    except Exception as e:
                                        _LOGGER.error("Failed to parse retry response: %s", e)
                                        raise Exception("Server returned invalid response on retry")
                                    
                                    _LOGGER.debug("Retry login response: %s", retry_response)
                                    
                                    if retry_response.get("status") != "ok":
                                        _LOGGER.error("Retry login error: %s", retry_response.get("status"))
                                        raise Exception(f"Login error after session logout")
                                    
                                    login_response = retry_response
                            except aiohttp.ClientError as e:
                                _LOGGER.error("Retry login connection error: %s", e)
                                raise Exception(f"Connection error after logout: {e}")
                            except Exception as e:
                                _LOGGER.error("Retry login error: %s", e)
                                raise
                        else:
                            _LOGGER.error("Invalid credentials or server error: %s", error_status)
                            raise Exception(f"Invalid credentials or server error")
                    
                    sid = login_response.get("sid")
                    if not sid:
                        _LOGGER.error("No session ID in login response")
                        raise Exception("No session ID in login response")
                    
                    _LOGGER.debug("Login successful, SID: %s", sid)
                    
                    # Logout
                    headers = {"Cookie": f"PHPSESSID={sid}"}
                    logout_url = f"{server_url}api/?method=logout"
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
