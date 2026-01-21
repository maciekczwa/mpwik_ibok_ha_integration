"""Sensor platform for MPWIK iBOK integration."""
import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .coordinator import MPWIKIBOKCoordinator

_LOGGER = logging.getLogger(__name__)

CURRENCY_PLN = "PLN"
UNIT_CUBIC_METERS = "m³"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        BalanceSensor(coordinator, entry),
        InvoiceNumberSensor(coordinator, entry),
        InvoiceDueDateSensor(coordinator, entry),
        InvoiceAmountOwedSensor(coordinator, entry),
        InvoiceGrossAmountSensor(coordinator, entry),
        MeterStateSensor(coordinator, entry),
        MeterReadoutDateSensor(coordinator, entry),
        MeterConsumptionSensor(coordinator, entry),
    ]
    
    async_add_entities(entities)


class IBOKSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for MPWIK iBOK sensors."""

    def __init__(self, coordinator: MPWIKIBOKCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_has_entity_name = True

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": "MPWIK iBOK",
            "manufacturer": "MPWIK",
        }

    def _get_data(self, key: str, default=None):
        """Safely get data value from coordinator."""
        if self.coordinator.data is None:
            return default
        return self.coordinator.data.get(key, default)


class BalanceSensor(IBOKSensorBase):
    """Sensor for account balance."""

    _attr_name = "Balance"
    _attr_native_unit_of_measurement = CURRENCY_PLN
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:currency-usd"

    def __init__(self, coordinator: MPWIKIBOKCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_balance"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        return self._get_data("balance")


class InvoiceNumberSensor(IBOKSensorBase):
    """Sensor for last invoice number."""

    _attr_name = "Last Invoice Number"
    _attr_icon = "mdi:receipt"

    def __init__(self, coordinator: MPWIKIBOKCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_invoice_number"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        invoice = self._get_data("last_invoice")
        if invoice:
            return invoice.get("invoice_number", "N/A")
        return None


class InvoiceDueDateSensor(IBOKSensorBase):
    """Sensor for last invoice due date."""

    _attr_name = "Last Invoice Due Date"
    _attr_icon = "mdi:calendar"

    def __init__(self, coordinator: MPWIKIBOKCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_invoice_due_date"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        invoice = self._get_data("last_invoice")
        if invoice:
            return invoice.get("due_date", "N/A")
        return None


class InvoiceAmountOwedSensor(IBOKSensorBase):
    """Sensor for last invoice amount owed."""

    _attr_name = "Last Invoice Amount Owed"
    _attr_native_unit_of_measurement = CURRENCY_PLN
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:cash"

    def __init__(self, coordinator: MPWIKIBOKCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_invoice_amount_owed"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        invoice = self._get_data("last_invoice")
        if invoice:
            try:
                value = invoice.get("amount_owed")
                return float(value) if value is not None else None
            except (ValueError, TypeError):
                return None
        return None


class InvoiceGrossAmountSensor(IBOKSensorBase):
    """Sensor for last invoice gross amount."""

    _attr_name = "Last Invoice Gross Amount"
    _attr_native_unit_of_measurement = CURRENCY_PLN
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:receipt"

    def __init__(self, coordinator: MPWIKIBOKCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_invoice_gross_amount"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        invoice = self._get_data("last_invoice")
        if invoice:
            try:
                value = invoice.get("gross_amount")
                return float(value) if value is not None else None
            except (ValueError, TypeError):
                return None
        return None


class MeterStateSensor(IBOKSensorBase):
    """Sensor for current meter reading."""

    _attr_name = "Meter Reading"
    _attr_native_unit_of_measurement = UNIT_CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = "water"
    _attr_icon = "mdi:water-meter"

    def __init__(self, coordinator: MPWIKIBOKCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_meter_state"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        meter_state = self._get_data("meter_state")
        if meter_state and meter_state != "N/A":
            try:
                return float(meter_state)
            except (ValueError, TypeError):
                return None
        return None


class MeterReadoutDateSensor(IBOKSensorBase):
    """Sensor for last meter readout date."""

    _attr_name = "Last Meter Readout Date"
    _attr_icon = "mdi:calendar"

    def __init__(self, coordinator: MPWIKIBOKCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_readout_date"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        readout_date = self._get_data("readout_date")
        if readout_date:
            return readout_date
        return None


class MeterConsumptionSensor(IBOKSensorBase):
    """Sensor for meter consumption since last reading."""

    _attr_name = "Meter Consumption"
    _attr_native_unit_of_measurement = UNIT_CUBIC_METERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:water"

    def __init__(self, coordinator: MPWIKIBOKCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_meter_consumption"

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        consumption = self._get_data("consumption")
        if consumption and consumption != "N/A":
            try:
                return float(consumption)
            except (ValueError, TypeError):
                return None
        return None
