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
- 🔧 **Standalone API client** - Test API without installing Home Assistant

## Standalone API Usage

The integration includes a standalone API client that can be used independently of Home Assistant. This is useful for:
- Testing your MPWIK iBOK credentials
- Integrating with other systems
- Debugging connection issues
- Building custom applications

See the [examples](examples/) directory for detailed usage instructions and sample scripts.

**Quick test:**
```bash
pip install aiohttp
python examples/test_api.py https://ibok.mpwik.bedzin.pl your_username your_password
```

For more details, see [examples/README.md](examples/README.md).

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

### Notify when you owe money (balance > 0)

```yaml
- alias: "MPWIK Debt Notification"
  trigger:
    - platform: numeric_state
      entity_id: sensor.mpwik_ibok_balance
      above: 0
  action:
    - service: notify.notify
      data:
        message: "⚠️ MPWIK: You owe {{ states('sensor.mpwik_ibok_balance') }} PLN"
```

**Note:** In MPWIK system, a positive balance means you have a DEBT and need to pay. Zero or negative balance means you've paid everything.

## Example Automations

### Notify when you owe money (balance > 0)

```yaml
- alias: "MPWIK Debt Alert"
  trigger:
    - platform: numeric_state
      entity_id: sensor.mpwik_ibok_balance
      above: 0
  action:
    - service: notify.notify
      data:
        message: "⚠️ MPWIK: You have a debt of {{ states('sensor.mpwik_ibok_balance') }} PLN to pay!"
```

**Important:** In the MPWIK system:
- **Positive balance (> 0)** = You OWE money and must PAY
- **Zero or negative balance (≤ 0)** = You've paid everything, account is settled

### Notify when invoice is due soon

```yaml
- alias: "Invoice Due Soon Notification"
  trigger:
    - platform: template
      value_template: "{{ states('sensor.mpwik_ibok_last_invoice_due_date') != 'N/A' }}"
  condition:
    - condition: template
      value_template: "{{ (states('sensor.mpwik_ibok_balance') | float(0)) > 0 }}"
  action:
    - service: notify.notify
      data:
        message: "📋 MPWIK invoice due on {{ states('sensor.mpwik_ibok_last_invoice_due_date') }}, you owe {{ states('sensor.mpwik_ibok_last_invoice_amount_owed') }} PLN"
```

### Alert when meter reading is due (no reading for 30+ days)

```yaml
- alias: "Meter Reading Overdue Alert"
  trigger:
    - platform: template
      value_template: >
        {% set last_date = states('sensor.mpwik_ibok_last_meter_readout_date') %}
        {% if last_date != 'N/A' %}
          {{ (now() - strptime(last_date, '%Y-%m-%d')).days > 30 }}
        {% else %}
          false
        {% endif %}
  action:
    - service: notify.notify
      data:
        message: "📊 MPWIK: Last meter reading was on {{ states('sensor.mpwik_ibok_last_meter_readout_date') }}. Please submit a new reading!"
```

## Support

For issues and feature requests, please visit: https://github.com/maciekczwa/mpwik_ibok_ha_integration/issues

## License

MIT License - See LICENSE file for details

## Author

maciekczwa
