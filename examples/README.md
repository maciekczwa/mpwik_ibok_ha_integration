# MPWIK iBOK API Examples

This directory contains example scripts demonstrating how to use the MPWIK iBOK API client standalone, without Home Assistant.

## Prerequisites

The API client requires:
- Python 3.8 or higher
- `aiohttp` library

Install dependencies:
```bash
pip install aiohttp
```

## test_api.py

A comprehensive example script that demonstrates all API functionality.

### Usage

```bash
python test_api.py <server_url> <username> <password>
```

### Example

```bash
python test_api.py https://ibok.mpwik.bedzin.pl user@example.com mypassword
```

### What it does

The script demonstrates three different approaches to using the API:

1. **Manual login/logout**: Explicitly calling `login()` and `logout()` methods
2. **Context manager**: Using `async with` for automatic login/logout
3. **Convenience method**: Using `get_all_data()` to fetch all data in one call

For each approach, it:
- Logs in to the MPWIK iBOK server
- Fetches account balance
- Retrieves invoice information
- Gets meter readings
- Logs out

### Output

The script provides detailed logging of all API operations and prints a summary at the end showing:
- Current balance (with debt warning if applicable)
- Number of invoices
- Latest meter reading and consumption

## Using the API in Your Own Scripts

Here's a simple example of how to use the API client in your own Python scripts:

```python
import asyncio
from custom_components.mpwik_ibok.api_client import MPWIKIBOKApiClient

async def check_balance():
    # Create client
    client = MPWIKIBOKApiClient(
        server_url="https://ibok.mpwik.bedzin.pl",
        username="your_username",
        password="your_password"
    )
    
    # Option 1: Manual control
    await client.login()
    balance = await client.get_balance()
    invoices = await client.get_invoices()
    meter_data = await client.get_meter_readouts()
    await client.logout()
    
    print(f"Balance: {balance} PLN")
    print(f"Invoices: {len(invoices)}")
    
    # Option 2: Using context manager (recommended)
    async with MPWIKIBOKApiClient(server_url, username, password) as client:
        balance = await client.get_balance()
        print(f"Balance: {balance} PLN")
    
    # Option 3: Get all data at once
    data = await client.get_all_data()
    print(f"Balance: {data['balance']} PLN")
    print(f"Last invoice: {data['last_invoice']}")

# Run the async function
asyncio.run(check_balance())
```

## API Client Methods

The `MPWIKIBOKApiClient` class provides the following methods:

### Authentication
- `login()`: Authenticate with the MPWIK iBOK server
- `logout()`: End the session
- Context manager support via `async with`

### Data Retrieval
- `get_balance()`: Get current account balance (float)
- `get_invoices()`: Get list of invoices (list of dicts)
- `get_meter_readouts()`: Get meter reading information (dict)
- `get_all_data()`: Fetch all data in one call (dict)

### Error Handling

The API client raises specific exceptions:
- `MPWIKIBOKAuthError`: Authentication failures
- `MPWIKIBOKConnectionError`: Network/connection issues
- `MPWIKIBOKApiError`: General API errors

## Integration with Home Assistant

While these examples show standalone usage, the API client is also used by the Home Assistant integration located in `custom_components/mpwik_ibok/`. The integration uses the same API client with a coordinator wrapper for Home Assistant-specific functionality.
