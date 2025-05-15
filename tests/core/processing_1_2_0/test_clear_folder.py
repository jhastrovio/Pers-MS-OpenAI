import asyncio
from core.utils.onedrive_utils import clear_folder
from core.utils.config import config

async def test_clear_folder():
    """Test clearing the processed emails folder."""
    print("\nTesting folder clearing...")
    
    # Clear the processed emails folder
    folder = config["onedrive"]["processed_emails_folder"]
    print(f"Clearing folder: {folder}")
    await clear_folder(folder)
    
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(test_clear_folder()) 