"""
Asset Management Platform System Test
"""

import asyncio
import httpx
import sys
import os

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.market_data_service import market_data_service
from app.database.redis_client import redis_client


async def test_market_data():
    """Test market data service"""
    print("🔍 Testing Market Data Service...")
    
    try:
        # Test single stock price
        print("  📈 Testing single stock price (SPY)...")
        spy_price = await market_data_service.get_stock_price("SPY")
        if spy_price:
            print(f"    ✅ SPY Price: ${spy_price['price']}")
        else:
            print("    ❌ Failed to get SPY price")
        
        # Test multiple stock prices
        print("  📊 Testing multiple stock prices...")
        symbols = ["SPY", "QQQ", "NVDA"]
        prices = await market_data_service.get_multiple_prices(symbols)
        if prices:
            for symbol, data in prices.items():
                if data:
                    print(f"    ✅ {symbol}: ${data['price']}")
                else:
                    print(f"    ❌ Failed to get {symbol} price")
        
        # Test S&P 500 data
        print("  📈 Testing S&P 500 indicators...")
        sp500_data = await market_data_service.get_sp500_data()
        if sp500_data:
            print(f"    ✅ S&P 500: ${sp500_data['price']}, SMA(200): ${sp500_data['sma_200']:.2f}")
            print(f"    📊 Below SMA: {sp500_data['below_sma']}")
        else:
            print("    ❌ Failed to get S&P 500 data")
        
        # Test VIX data
        print("  😰 Testing VIX data...")
        vix_data = await market_data_service.get_vix_data()
        if vix_data:
            print(f"    ✅ VIX: {vix_data['price']}")
        else:
            print("    ❌ Failed to get VIX data")
        
        # Test exchange rate
        print("  💱 Testing exchange rate...")
        rate = await market_data_service.get_exchange_rate()
        if rate:
            print(f"    ✅ USD/CNY: {rate}")
        else:
            print("    ❌ Failed to get exchange rate")
        
        print("✅ Market Data Service test completed\n")
        
    except Exception as e:
        print(f"❌ Market Data Service test failed: {e}\n")


def test_redis():
    """Test Redis connection"""
    print("🔄 Testing Redis Connection...")
    
    try:
        # Test basic connection
        if redis_client.ping():
            print("  ✅ Redis connection successful")
        else:
            print("  ❌ Redis connection failed")
            return False
        
        # Test set/get
        test_key = "test_key"
        test_value = {"test": "data", "timestamp": "2024-01-01"}
        
        if redis_client.set(test_key, test_value, ttl=60):
            print("  ✅ Redis set operation successful")
        else:
            print("  ❌ Redis set operation failed")
            return False
        
        retrieved_value = redis_client.get(test_key)
        if retrieved_value == test_value:
            print("  ✅ Redis get operation successful")
        else:
            print("  ❌ Redis get operation failed")
            return False
        
        # Clean up
        redis_client.delete(test_key)
        print("✅ Redis Connection test completed\n")
        return True
        
    except Exception as e:
        print(f"❌ Redis Connection test failed: {e}\n")
        return False


async def test_api_endpoints():
    """Test API endpoints"""
    print("🌐 Testing API Endpoints...")
    
    base_url = "http://localhost:8000"
    
    try:
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            print("  🔍 Testing health endpoint...")
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("  ✅ Health endpoint working")
            else:
                print(f"  ❌ Health endpoint failed: {response.status_code}")
            
            # Test root endpoint
            print("  🏠 Testing root endpoint...")
            response = await client.get(f"{base_url}/")
            if response.status_code == 200:
                print("  ✅ Root endpoint working")
            else:
                print(f"  ❌ Root endpoint failed: {response.status_code}")
            
            # Test market data endpoints
            print("  📊 Testing market data endpoints...")
            response = await client.get(f"{base_url}/api/v1/market/prices/SPY")
            if response.status_code == 200:
                print("  ✅ Market data endpoint working")
            else:
                print(f"  ❌ Market data endpoint failed: {response.status_code}")
        
        print("✅ API Endpoints test completed\n")
        
    except httpx.ConnectError:
        print("  ⚠️  Server not running. Start with: uvicorn app.main:app --reload\n")
    except Exception as e:
        print(f"❌ API Endpoints test failed: {e}\n")


def test_config():
    """Test configuration"""
    print("⚙️  Testing Configuration...")
    
    try:
        from app.config import settings, get_all_symbols, get_symbol_category
        
        print(f"  ✅ App Name: {settings.app_name}")
        print(f"  ✅ App Version: {settings.app_version}")
        print(f"  ✅ Database URL: {settings.database_url}")
        print(f"  ✅ Redis URL: {settings.redis_url}")
        
        # Test target allocation
        print("  📊 Target Allocation:")
        for category, info in settings.target_allocation.items():
            print(f"    {category}: {info['target']*100}% - {info['symbols']}")
        
        # Test symbol functions
        all_symbols = get_all_symbols()
        print(f"  ✅ All symbols count: {len(all_symbols)}")
        
        spy_category = get_symbol_category("SPY")
        print(f"  ✅ SPY category: {spy_category}")
        
        print("✅ Configuration test completed\n")
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}\n")


async def main():
    """Main test function"""
    print("🚀 Asset Management Platform System Test\n")
    print("=" * 50)
    
    # Test configuration
    test_config()
    
    # Test Redis
    redis_ok = test_redis()
    
    # Test market data (if Redis is working)
    if redis_ok:
        await test_market_data()
    
    # Test API endpoints
    await test_api_endpoints()
    
    print("=" * 50)
    print("🎉 System test completed!")
    print("\n📝 Next steps:")
    print("1. Start the server: uvicorn app.main:app --reload")
    print("2. Visit API docs: http://localhost:8000/docs")
    print("3. Create demo user: POST /api/v1/auth/create-demo-user")
    print("4. Create demo holdings: POST /api/v1/portfolio/holdings/{user_id}/demo-data")
    print("5. Check strategy dashboard: GET /api/v1/strategy/dashboard/{user_id}")


if __name__ == "__main__":
    asyncio.run(main()) 