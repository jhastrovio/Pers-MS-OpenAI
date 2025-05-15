import asyncio
from core.graph_1_1_0.main import GraphClient

async def main():
    client = GraphClient()
    # Create a temporary file for testing
    with open('test_manual_upload.txt', 'w') as f:
        f.write('This is a test file for manual upload.')
    
    try:
        response = await client.save_to_onedrive('test_manual_upload.txt', 'test_manual_upload.txt')
        print('Upload response:', response)
    except Exception as e:
        print('Error during upload:', e)

if __name__ == '__main__':
    asyncio.run(main()) 