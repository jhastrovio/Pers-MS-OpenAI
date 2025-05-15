import os
import asyncio
from core.auth import MSGraphAuth
from core.data_access import DataAccess
from core.models import SearchQuery

# Set the author you want to filter by
AUTHOR_TO_FILTER = "thomas.stolper@systemacro.com"  # Change as needed

async def main():
    auth = MSGraphAuth(
        client_id=os.environ["CLIENT_ID"],
        client_secret=os.environ["CLIENT_SECRET"],
        tenant_id=os.environ["TENANT_ID"]
    )
    data_access = DataAccess(auth=auth)
    query = SearchQuery(query="", filters={"author": AUTHOR_TO_FILTER}, limit=20)
    results = await data_access.search_data(query)
    print(f"Found {len(results.results)} results for author '{AUTHOR_TO_FILTER}':")
    for entry in results.results:
        print(entry.metadata)
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main()) 