import asyncio
from pathlib import Path
from crawlerutils import Cacher

# Configure the cache directory and register the cacher
Cacher.register(proxy="http://127.0.0.1:7890")
Cacher.fix_blob()

# Synchronous usage example
def synchronous_example():
    url = "https://www.example.com"
    result_file = Path("result_sync.html")
    Cacher.download(url=url, file=result_file)
    print(f"Synchronous download complete. File saved to {result_file}")
    data = Cacher.get(url)
    print(f"Synchronous get complete. Data length: {len(data)}")
    result_file.unlink()

# Asynchronous usage example
async def asynchronous_example():
    url = "https://www.example.com"
    result_file = Path("result_async.html")
    await Cacher.adownload(url=url, file=result_file)
    print(f"Asynchronous download complete. File saved to {result_file}")
    data = await Cacher.aget(url)
    print(f"Asynchronous get complete. Data length: {len(data)}")
    result_file.unlink()

if __name__ == "__main__":
    synchronous_example()
    asyncio.run(asynchronous_example())
