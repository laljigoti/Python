from concurrent.futures import ThreadPoolExecutor
import asyncio
import time
async def work(url):
    # do stuff
    return f"Result for {url}"

async def run():
    urls = ["http://cafecito.tech", "http://medium.com", "http://demo.com"]
    tasks = [work(url) for url in urls]
    results = await asyncio.gather(*tasks)
    print(f"Results: {results}")

#asyncio.run(run())
# -----------------------------------------------------------------------------------------
# Passing Return Value to Another Function In the Sample Context
# ----------------------------------------------------------------------------
def fetch_data(Name:str):  
    time.sleep(5)  
    return f"Hello from {Name}"

def process_data(data):
    # do stuff
    print(f"Processed data: {data}")

def run1():
    with ThreadPoolExecutor(max_workers=2) as executor:
        print('Thread started')
        future1 = executor.submit(fetch_data, 'Lalji')
        print('Waiting for result from fetch data')
        # Wait for result and feed it to the second function
        res = future1.result()
        executor.submit(process_data, res)


    print("Pipeline completed")
run1()
