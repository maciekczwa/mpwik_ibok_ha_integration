"""Config flow for MPWIK iBOK integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api_client import MPWIKIBOKApiClient, MPWIKIBOKApiError, MPWIKIBOKAuthError, MPWIKIBOKConnectionError

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
        username = user_input.get("username")
        password = user_input.get("password")
        server_url = user_input.get("server_url").strip()
        
        # Normalize the URL (API client will handle trailing slash)
        user_input["server_url"] = server_url
        
        _LOGGER.debug("Validating with server_url: %s", server_url)
        
        try:
            # Create API client and test login
            api_client = MPWIKIBOKApiClient(
                server_url=server_url,
                username=username,
                password=password,
                timeout=30,
            )
            
            # Test login and logout explicitly
            await api_client.login()
            _LOGGER.debug("Login successful during validation")
            await api_client.logout()
            _LOGGER.debug("Logout successful during validation")
                
        except MPWIKIBOKAuthError as e:
            _LOGGER.error("Authentication error: %s", e)
            raise Exception("Invalid credentials or server error")
        except MPWIKIBOKConnectionError as e:
            _LOGGER.error("Connection error: %s", e)
            raise Exception(f"Connection error: {e}")
        except MPWIKIBOKApiError as e:
            _LOGGER.error("API error: %s", e)
            raise Exception(f"API error: {e}")
        except Exception as e:
            _LOGGER.error("Validation error: %s", e)
            raise
