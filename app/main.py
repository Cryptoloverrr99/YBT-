import asyncio,logging
from .scanner import MultiTFScanner
logging.basicConfig(level=logging.INFO,format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
async def main(): await MultiTFScanner().run_forever()
if __name__=='__main__': asyncio.run(main())
