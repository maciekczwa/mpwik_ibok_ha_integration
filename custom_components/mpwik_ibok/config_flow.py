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
                    vol.Optional("server_url", default="https://ibok.mpwik.bedzin.pl"): str,
                }
            ),
            errors=errors,
            description_placeholders={},
        )
    
    async def _validate_input(self, user_input: Dict[str, Any]) -> None:
        """Validate the user input allows us to connect."""
        import aiohttp
        
        username = user_input.get("username")
        password = user_input.get("password")
        server_url = user_input.get("server_url", "https://ibok.mpwik.bedzin.pl")
        
        async with aiohttp.ClientSession() as session:
            login_data = {
                "user": username.lower().strip(),
                "pass": password
            }
            
            async with session.post(
                f"{server_url}/api/?method=login",
                data=login_data,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Login failed with status {resp.status}")
                
                login_response = await resp.json()
                
                if login_response.get("status") != "ok":
                    raise Exception(f"Invalid credentials")
                
                sid = login_response.get("sid")
                if not sid:
                    raise Exception("No session ID in login response")
                
                # Logout
                headers = {"Cookie": f"PHPSESSID={sid}"}
                try:
                    async with session.get(
                        f"{server_url}/api/?method=logout",
                        headers=headers,
                        ssl=False,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as logout_resp:
                        pass
                except Exception:
                    pass
