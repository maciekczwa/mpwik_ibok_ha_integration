#!/usr/bin/env python3
"""Example script demonstrating standalone API usage without Home Assistant.

This script shows how to use the MPWIKIBOKApiClient directly to interact
with the MPWIK iBOK API without needing Home Assistant installed.

Usage:
    python test_api.py <server_url> <username> <password>
    
Example:
    python test_api.py https://ibok.mpwik.bedzin.pl user@example.com mypassword
"""
import asyncio
import logging
import sys
import os

# Add the custom_components directory to the path to import the API client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'mpwik_ibok'))

from api_client import MPWIKIBOKApiClient, MPWIKIBOKApiError, MPWIKIBOKAuthError, MPWIKIBOKConnectionError


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_api(server_url: str, username: str, password: str):
    """Test the MPWIK iBOK API."""
    logger.info("=" * 60)
    logger.info("Testing MPWIK iBOK API")
    logger.info("=" * 60)
    logger.info(f"Server URL: {server_url}")
    logger.info(f"Username: {username}")
    logger.info("=" * 60)
    
    try:
        # Create API client
        client = MPWIKIBOKApiClient(
            server_url=server_url,
            username=username,
            password=password,
        )
        
        logger.info("\n1. Testing login...")
        await client.login()
        logger.info("✓ Login successful!")
        
        logger.info("\n2. Fetching account balance...")
        balance = await client.get_balance()
        logger.info(f"✓ Balance: {balance} PLN")
        if balance and balance > 0:
            logger.warning(f"⚠️  You have a debt of {balance} PLN to pay!")
        elif balance is not None:
            logger.info("✓ Account is settled (no debt)")
        
        logger.info("\n3. Fetching invoices...")
        invoices = await client.get_invoices()
        if invoices:
            logger.info(f"✓ Found {len(invoices)} invoice(s)")
            for i, invoice in enumerate(invoices, 1):
                logger.info(f"\n   Invoice {i}:")
                logger.info(f"     Number: {invoice['invoice_number']}")
                logger.info(f"     Due date: {invoice['due_date']}")
                logger.info(f"     Amount owed: {invoice['amount_owed']} PLN")
                logger.info(f"     Gross amount: {invoice['gross_amount']} PLN")
                logger.info(f"     Net amount: {invoice['net_amount']} PLN")
                logger.info(f"     VAT: {invoice['vat']} PLN")
        else:
            logger.info("✓ No invoices found")
        
        logger.info("\n4. Fetching meter readouts...")
        meter_data = await client.get_meter_readouts()
        if meter_data.get('meter_state'):
            logger.info(f"✓ Meter reading: {meter_data['meter_state']} m³")
            logger.info(f"  Readout date: {meter_data.get('readout_date', 'N/A')}")
            logger.info(f"  Consumption: {meter_data.get('consumption', 'N/A')} m³")
        else:
            logger.info("✓ No meter data available")
        
        logger.info("\n5. Logging out...")
        await client.logout()
        logger.info("✓ Logout successful!")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ All tests completed successfully!")
        logger.info("=" * 60)
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Balance: {balance} PLN")
        if balance and balance > 0:
            print(f"Status: ⚠️  DEBT - You owe {balance} PLN")
        elif balance is not None:
            print("Status: ✓ Account settled")
        else:
            print("Status: Unknown")
        print(f"Invoices: {len(invoices) if invoices else 0}")
        if meter_data.get('meter_state'):
            print(f"Meter: {meter_data['meter_state']} m³ (as of {meter_data.get('readout_date', 'N/A')})")
        print("=" * 60)
        
        return True
        
    except MPWIKIBOKAuthError as e:
        logger.error(f"✗ Authentication failed: {e}")
        logger.error("Please check your username and password.")
        return False
    except MPWIKIBOKConnectionError as e:
        logger.error(f"✗ Connection failed: {e}")
        logger.error("Please check your server URL and network connection.")
        return False
    except MPWIKIBOKApiError as e:
        logger.error(f"✗ API error: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}", exc_info=True)
        return False


async def test_api_with_context_manager(server_url: str, username: str, password: str):
    """Test the MPWIK iBOK API using context manager (alternative approach)."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing with context manager (async with)")
    logger.info("=" * 60)
    
    try:
        async with MPWIKIBOKApiClient(server_url, username, password) as client:
            logger.info("✓ Logged in via context manager")
            
            # Fetch all data
            balance = await client.get_balance()
            logger.info(f"✓ Balance: {balance} PLN")
            
        logger.info("✓ Automatically logged out when exiting context")
        return True
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False


async def test_all_data_method(server_url: str, username: str, password: str):
    """Test the convenience method to get all data at once."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing get_all_data() convenience method")
    logger.info("=" * 60)
    
    try:
        client = MPWIKIBOKApiClient(server_url, username, password)
        data = await client.get_all_data()
        
        logger.info("✓ Retrieved all data in one call:")
        logger.info(f"  Balance: {data.get('balance')} PLN")
        logger.info(f"  Last invoice: {data.get('last_invoice')}")
        logger.info(f"  Meter state: {data.get('meter_state')} m³")
        logger.info(f"  Readout date: {data.get('readout_date')}")
        logger.info(f"  Consumption: {data.get('consumption')} m³")
        
        return True
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False


def main():
    """Main function."""
    if len(sys.argv) != 4:
        print("Usage: python test_api.py <server_url> <username> <password>")
        print("\nExample:")
        print("  python test_api.py https://ibok.mpwik.bedzin.pl user@example.com mypassword")
        sys.exit(1)
    
    server_url = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    # Run all tests
    print("\nStarting API tests...\n")
    
    success1 = asyncio.run(test_api(server_url, username, password))
    success2 = asyncio.run(test_api_with_context_manager(server_url, username, password))
    success3 = asyncio.run(test_all_data_method(server_url, username, password))
    
    if success1 and success2 and success3:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
