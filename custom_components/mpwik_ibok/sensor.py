"""Sensor platform for MPWIK iBOK integration."""
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import IBOKDataUpdateCoordinator
from .const import DOMAIN

CURRENCY_PLN = "PLN"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: IBOKDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        BalanceSensor(coordinator, entry),
        InvoiceNumberSensor(coordinator, entry),
        InvoiceDueDateSensor(coordinator, entry),
        InvoiceAmountOwedSensor(coordinator, entry),
        InvoiceGrossAmountSensor(coordinator, entry),
    ]
    
    async_add_entities(entities)


class BalanceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for account balance."""
    
    _attr_name = "Balance"
    _attr_unique_id = "mpwik_ibok_balance"
    _attr_native_unit_of_measurement = CURRENCY_PLN
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:currency-usd"
    
    def __init__(self, coordinator: IBOKDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_balance"
        self._attr_name = f"MPWIK iBOK Balance"
    
    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("balance", 0)


class InvoiceNumberSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last invoice number."""
    
    _attr_name = "Last Invoice Number"
    _attr_unique_id = "mpwik_ibok_invoice_number"
    _attr_icon = "mdi:receipt"
    
    def __init__(self, coordinator: IBOKDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_invoice_number"
        self._attr_name = f"MPWIK iBOK Last Invoice Number"
    
    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        invoice = self.coordinator.data.get("last_invoice")
        if invoice:
            return invoice.get("invoice_number", "N/A")
        return "N/A"


class InvoiceDueDateSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last invoice due date."""
    
    _attr_name = "Last Invoice Due Date"
    _attr_unique_id = "mpwik_ibok_invoice_due_date"
    _attr_icon = "mdi:calendar-clock"
    
    def __init__(self, coordinator: IBOKDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_invoice_due_date"
        self._attr_name = f"MPWIK iBOK Last Invoice Due Date"
    
    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        invoice = self.coordinator.data.get("last_invoice")
        if invoice:
            return invoice.get("due_date", "N/A")
        return "N/A"


class InvoiceAmountOwedSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last invoice amount owed."""
    
    _attr_name = "Last Invoice Amount Owed"
    _attr_unique_id = "mpwik_ibok_invoice_amount_owed"
    _attr_native_unit_of_measurement = CURRENCY_PLN
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:cash"
    
    def __init__(self, coordinator: IBOKDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_invoice_amount_owed"
        self._attr_name = f"MPWIK iBOK Last Invoice Amount Owed"
    
    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        invoice = self.coordinator.data.get("last_invoice")
        if invoice:
            try:
                return float(invoice.get("amount_owed", 0))
            except (ValueError, TypeError):
                return 0
        return 0


class InvoiceGrossAmountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last invoice gross amount."""
    
    _attr_name = "Last Invoice Gross Amount"
    _attr_unique_id = "mpwik_ibok_invoice_gross_amount"
    _attr_native_unit_of_measurement = CURRENCY_PLN
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:receipt"
    
    def __init__(self, coordinator: IBOKDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_invoice_gross_amount"
        self._attr_name = f"MPWIK iBOK Last Invoice Gross Amount"
    
    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        invoice = self.coordinator.data.get("last_invoice")
        if invoice:
            try:
                return float(invoice.get("gross_amount", 0))
            except (ValueError, TypeError):
                return 0
        return 0
