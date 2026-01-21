# MPWIK iBOK Integration for Home Assistant

A Home Assistant integration for monitoring your MPWIK iBOK utility account balance and invoices.

## Features

- 🔐 Secure login with username and password
- 💰 Monitor your account balance
- 📄 Track last invoice details:
  - Invoice number
  - Due date
  - Amount owed
  - Gross amount
- 🔄 Automatic updates every 24 hours
- 🔌 Customizable server URL
- 📦 HACS compatible

## Installation

### Via HACS (Recommended)

1. Go to HACS > Integrations
2. Click "Custom repositories"
3. Add: `https://github.com/maciekczwa/mpwik_ibok_ha_integration`
4. Category: Integration
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/mpwik_ibok` folder
2. Place it in your `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services > Create Automation
2. Click "Create Integration"
3. Search for "MPWIK iBOK"
4. Enter your credentials:
   - **Username**: Your iBOK username (email)
   - **Password**: Your iBOK password
   - **Server URL**: Your MPWIK iBOK server URL (e.g., https://ibok.mpwik.bedzin.pl)

## Sensors

After setup, the following sensors are available:

- `sensor.mpwik_ibok_balance` - Current account balance (PLN)
- `sensor.mpwik_ibok_last_invoice_number` - Last invoice number
- `sensor.mpwik_ibok_last_invoice_due_date` - Last invoice due date
- `sensor.mpwik_ibok_last_invoice_amount_owed` - Amount owed on last invoice (PLN)
- `sensor.mpwik_ibok_last_invoice_gross_amount` - Gross amount of last invoice (PLN)

## Update Frequency

The integration updates automatically every 24 hours. You can manually trigger an update by going to Developer Tools > YAML and calling the `homeassistant.update_entity` service.

## Example Automations

### Notify when balance is low

```yaml
- alias: "Low MPWIK Balance Notification"
  trigger:
    - platform: numeric_state
      entity_id: sensor.mpwik_ibok_balance
      below: 100
  action:
    - service: notify.notify
      data:
        message: "Your MPWIK balance is low: {{ states('sensor.mpwik_ibok_balance') }} PLN"
```

### Notify when invoice is due soon

```yaml
- alias: "Invoice Due Notification"
  trigger:
    - platform: template
      value_template: "{{ states('sensor.mpwik_ibok_last_invoice_due_date') != 'N/A' }}"
  condition:
    - condition: template
      value_template: "{{ (states('sensor.mpwik_ibok_last_invoice_amount_owed') | float(0)) > 0 }}"
  action:
    - service: notify.notify
      data:
        message: "MPWIK invoice due on {{ states('sensor.mpwik_ibok_last_invoice_due_date') }}"
```

## Support

For issues and feature requests, please visit: https://github.com/maciekczwa/mpwik_ibok_ha_integration/issues

## License

MIT License - See LICENSE file for details

## Author

maciekczwa
