# Installation & Setup Guide

## MPWIK iBOK Integration for Home Assistant

### Quick Start

#### Option 1: HACS Installation (Recommended)

1. Ensure HACS is installed in Home Assistant
2. Go to **HACS** → **Integrations**
3. Click the three dots in the top right → **Custom repositories**
4. Add repository URL: `https://github.com/maciekczwa/mpwik_ibok_ha_integration`
5. Select **Integration** as category
6. Click **Install**
7. Restart Home Assistant

#### Option 2: Manual Installation

1. Download the repository as ZIP
2. Extract the `custom_components/mpwik_ibok` folder
3. Place it in your Home Assistant `custom_components` folder:
   ```
   ~/.homeassistant/custom_components/mpwik_ibok/
   ```
4. Restart Home Assistant

### Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Create Integration**
3. Search for **"MPWIK iBOK"**
4. Click it and fill in:
   - **Username**: Your iBOK email/username
   - **Password**: Your iBOK password
   - **Server URL**: Your MPWIK iBOK server URL (e.g., https://ibok.mpwik.bedzin.pl)
5. Click **Submit**

### Verify Installation

After setup, check if sensors are available:

1. Go to **Settings** → **Devices & Services** → **Entities**
2. Search for `mpwik_ibok`
3. You should see 5 sensors:
   - `sensor.mpwik_ibok_balance`
   - `sensor.mpwik_ibok_last_invoice_number`
   - `sensor.mpwik_ibok_last_invoice_due_date`
   - `sensor.mpwik_ibok_last_invoice_amount_owed`
   - `sensor.mpwik_ibok_last_invoice_gross_amount`

### Troubleshooting

#### Integration not found
- Clear Home Assistant cache: **Settings** → **Developer Tools** → **YAML** → reload custom components
- Restart Home Assistant
- Check that `custom_components/mpwik_ibok` folder exists with all files

#### Login fails
- Verify your username and password are correct
- Check if server URL is reachable
- Try the standalone Python script first to test credentials

#### No entities show up
- Check Home Assistant logs for errors
- Ensure update coordinator is running
- Wait for initial data update (can take up to 24 hours)

### Manual Updates

To force a data update without waiting 24 hours:

1. Go to **Developer Tools** → **States**
2. Filter for `mpwik_ibok`
3. Click on the `mpwik_ibok.{your_instance}` entity
4. Click **Call Service** → **homeassistant.update_entity**
5. Select the entity and click **Call Service**

### File Structure

```
mpwik_ibok_ha_integration/
├── custom_components/
│   └── mpwik_ibok/
│       ├── __init__.py          # Main integration logic
│       ├── config_flow.py       # Configuration flow
│       ├── sensor.py            # Sensor entities
│       ├── const.py             # Constants
│       ├── manifest.json        # Integration metadata
│       ├── strings.json         # UI strings/translations
│       └── py.typed             # Type hints marker
├── hacs.json                    # HACS metadata
├── README.md                    # Main documentation
├── LICENSE                      # MIT License
└── .gitignore                   # Git ignore rules
```

### Development

If you want to contribute or modify the integration:

1. Clone the repository
2. Make your changes
3. Test locally by copying to `custom_components/`
4. Submit a pull request

### Support

For issues and questions:
- GitHub Issues: https://github.com/maciekczwa/mpwik_ibok_ha_integration/issues
- Home Assistant Community: https://community.home-assistant.io/

### Privacy & Security

- Credentials are stored securely in Home Assistant
- All communication is over HTTPS
- No data is sent to third-party services
- Integration only connects to your configured MPWIK iBOK server
