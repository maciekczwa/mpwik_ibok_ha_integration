"""Data coordinator for MPWIK iBOK integration."""
import logging
from datetime import timedelta
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry

from .api_client import MPWIKIBOKApiClient, MPWIKIBOKApiError, MPWIKIBOKAuthError, MPWIKIBOKConnectionError

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(hours=24)
# Exponential backoff: 5min, 15min, 1h, 3h (max)
RETRY_BACKOFF_TIMES = [300, 900, 3600, 10800]


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

        _LOGGER.debug("Fetching data from %s", server_url)

        try:
            # Create API client
            api_client = MPWIKIBOKApiClient(
                server_url=server_url,
                username=username,
                password=password,
            )
            
            # Fetch all data using the API client
            data = await api_client.get_all_data()
            
            _LOGGER.debug("Returning data: %s", data)
            
            # Reset error tracking on successful update
            self.error_count = 0
            self.last_update_error_time = None
            
            return data
        
        except (MPWIKIBOKAuthError, MPWIKIBOKConnectionError, MPWIKIBOKApiError) as e:
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
            raise UpdateFailed(str(e))
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
