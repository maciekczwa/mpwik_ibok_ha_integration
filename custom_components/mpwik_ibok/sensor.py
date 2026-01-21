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
        MeterConsumptionSensor(hass, entry),
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
            "balance": None,
            "last_invoice": None,
            "meter_state": None,
            "readout_date": None,
            "consumption": None,
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
            # Set all data to None on error to trigger unavailable state
            self._data = {
                "balance": None,
                "last_invoice": None,
                "meter_state": None,
                "readout_date": None,
                "consumption": None,
            }
    
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
            
            # Fetch meter readout list
            meter_state = None
            readout_date = None
            consumption = None
            async with session.get(
                f"{server_url}/api/?method=readoutlist",
                headers=headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    meter_points = await resp.json()
                    if isinstance(meter_points, list) and len(meter_points) > 0:
                        meter_point = meter_points[0]
                        readouts = meter_point.get("readouts", [])
                        if readouts and len(readouts) > 0:
                            last_readout = readouts[0]
                            meter_state = last_readout.get("readoutvalue", None)
                            readout_date = last_readout.get("readoutdate", None)
                            consumption = last_readout.get("consumption", None)
            
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
                "balance": float(balance) if balance else None,
                "last_invoice": last_invoice,
                "meter_state": meter_state,
                "readout_date": readout_date,
                "consumption": consumption,
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
        balance = self._data.get("balance")
        if balance is None:
            return None
        return balance


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
                value = invoice.get("amount_owed")
                return float(value) if value is not None else None
            except (ValueError, TypeError):
                return None
        return None


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
                value = invoice.get("gross_amount")
                return float(value) if value is not None else None
            except (ValueError, TypeError):
                return None
        return None


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


class MeterConsumptionSensor(IBOKSensorBase):
    """Sensor for meter consumption since last reading."""
    
    _attr_name = "MPWIK iBOK Meter Consumption"
    _attr_native_unit_of_measurement = UNIT_CUBIC_METERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:water"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_meter_consumption"
    
    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        consumption = self._data.get("consumption")
        if consumption and consumption != "N/A":
            try:
                return float(consumption)
            except (ValueError, TypeError):
                return None
        return None
