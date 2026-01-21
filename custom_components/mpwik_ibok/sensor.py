"""Sensor platform for MPWIK iBOK integration."""
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import aiohttp
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CURRENCY_PLN = "PLN"
UPDATE_INTERVAL = timedelta(hours=24)
UNIT_CUBIC_METERS = "m³"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    entities = [
        BalanceSensor(hass, entry),
        InvoiceNumberSensor(hass, entry),
        InvoiceDueDateSensor(hass, entry),
        InvoiceAmountOwedSensor(hass, entry),
        InvoiceGrossAmountSensor(hass, entry),
        MeterStateSensor(hass, entry),
        MeterReadoutDateSensor(hass, entry),
    ]
    
    async_add_entities(entities)


class IBOKSensorBase(SensorEntity):
    """Base class for MPWIK iBOK sensors."""
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry
        self._attr_should_poll = True
        self._attr_update_interval = UPDATE_INTERVAL
        self._last_update = None
        self._data = {
            "balance": 0,
            "last_invoice": None,
        }
    
    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": "MPWIK iBOK",
            "manufacturer": "MPWIK",
        }
    
    async def async_update(self) -> None:
        """Update sensor data."""
        try:
            self._data = await self._fetch_data()
            self._last_update = datetime.now()
        except Exception as err:
            _LOGGER.error("Error updating MPWIK iBOK data: %s", err)
    
    async def _fetch_data(self) -> dict:
        """Fetch data from MPWIK iBOK API."""
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
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Login failed with status {resp.status}")
                
                login_response = await resp.json()
                
                if login_response.get("status") != "ok":
                    raise Exception(f"Login error: {login_response.get('status')}")
                
                sid = login_response.get("sid")
                if not sid:
                    raise Exception("No session ID in login response")
            
            # Fetch balance
            headers = {"Cookie": f"PHPSESSID={sid}"}
            
            balance = 0
            async with session.get(
                f"{server_url}/api/?method=balance",
                headers=headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    balance_response = await resp.json()
                    balance = balance_response.get("balance", 0)
            
            # Fetch invoices
            last_invoice = None
            async with session.get(
                f"{server_url}/api/?method=invoice",
                headers=headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    invoices = await resp.json()
                    if invoices and len(invoices) > 0:
                        inv = invoices[0]
                        last_invoice = {
                            "invoice_number": inv.get("nd", "N/A"),
                            "due_date": inv.get("pd", "N/A"),
                            "amount_owed": float(inv.get("owe", 0)),
                            "gross_amount": float(inv.get("brutto", 0)),
                            "net_amount": float(inv.get("netto", 0)),
                            "vat": float(inv.get("vat", 0))
                        }
            
            # Fetch meter readout
            meter_state = None
            readout_date = None
            async with session.get(
                f"{server_url}/api/?method=readout",
                headers=headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    readout_response = await resp.json()
                    readouts = readout_response.get("lastreadout", [])
                    if readouts and len(readouts) > 0:
                        readout = readouts[0]
                        meter_state = readout.get("couterdigits", "N/A")
                        readout_date = readout.get("date", "N/A")
            
            # Logout
            try:
                async with session.get(
                    f"{server_url}/api/?method=logout",
                    headers=headers,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    pass
            except Exception:
                pass  # Ignore logout errors
            
            return {
                "balance": float(balance),
                "last_invoice": last_invoice,
                "meter_state": meter_state,
                "readout_date": readout_date,
            }


class BalanceSensor(IBOKSensorBase):
    """Sensor for account balance."""
    
    _attr_name = "MPWIK iBOK Balance"
    _attr_native_unit_of_measurement = CURRENCY_PLN
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:currency-usd"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_balance"
    
    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self._data.get("balance", 0)


class InvoiceNumberSensor(IBOKSensorBase):
    """Sensor for last invoice number."""
    
    _attr_name = "MPWIK iBOK Last Invoice Number"
    _attr_icon = "mdi:receipt"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_invoice_number"
    
    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        invoice = self._data.get("last_invoice")
        if invoice:
            return invoice.get("invoice_number", "N/A")
        return "N/A"


class InvoiceDueDateSensor(IBOKSensorBase):
    """Sensor for last invoice due date."""
    
    _attr_name = "MPWIK iBOK Last Invoice Due Date"
    _attr_icon = "mdi:calendar-clock"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_invoice_due_date"
    
    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        invoice = self._data.get("last_invoice")
        if invoice:
            return invoice.get("due_date", "N/A")
        return "N/A"


class InvoiceAmountOwedSensor(IBOKSensorBase):
    """Sensor for last invoice amount owed."""
    
    _attr_name = "MPWIK iBOK Last Invoice Amount Owed"
    _attr_native_unit_of_measurement = CURRENCY_PLN
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:cash"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_invoice_amount_owed"
    
    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        invoice = self._data.get("last_invoice")
        if invoice:
            try:
                return float(invoice.get("amount_owed", 0))
            except (ValueError, TypeError):
                return 0
        return 0


class InvoiceGrossAmountSensor(IBOKSensorBase):
    """Sensor for last invoice gross amount."""
    
    _attr_name = "MPWIK iBOK Last Invoice Gross Amount"
    _attr_native_unit_of_measurement = CURRENCY_PLN
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:receipt"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_invoice_gross_amount"
    
    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        invoice = self._data.get("last_invoice")
        if invoice:
            try:
                return float(invoice.get("gross_amount", 0))
            except (ValueError, TypeError):
                return 0
        return 0


class MeterStateSensor(IBOKSensorBase):
    """Sensor for current meter reading."""
    
    _attr_name = "MPWIK iBOK Meter Reading"
    _attr_native_unit_of_measurement = UNIT_CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:water-meter"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_meter_state"
    
    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        meter_state = self._data.get("meter_state")
        if meter_state and meter_state != "N/A":
            try:
                return float(meter_state)
            except (ValueError, TypeError):
                return None
        return None


class MeterReadoutDateSensor(IBOKSensorBase):
    """Sensor for last meter readout date."""
    
    _attr_name = "MPWIK iBOK Last Meter Readout Date"
    _attr_icon = "mdi:calendar"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_readout_date"
    
    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        readout_date = self._data.get("readout_date")
        if readout_date:
            return readout_date
        return "N/A"
