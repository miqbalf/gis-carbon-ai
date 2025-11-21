"""Quick check of search method signature"""
import asyncio
import inspect
from planet import Session

async def check():
    async with Session() as s:
        c = s.client('data')
        print("Search method signature:")
        try:
            sig = inspect.signature(c.search)
            print(sig)
        except Exception as e:
            print(f"Error getting signature: {e}")
        
        print("\nSearch method docstring:")
        print(c.search.__doc__)
        
        # Check if create_search exists
        if hasattr(c, 'create_search'):
            print("\ncreate_search exists!")
            try:
                sig = inspect.signature(c.create_search)
                print(f"create_search signature: {sig}")
            except:
                pass

asyncio.run(check())

