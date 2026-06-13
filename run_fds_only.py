import sys
import logging
import time
import concurrent.futures
from etl_core.pipelines.fds import FdsPipeline

def run_fds():
    print('Starting isolated FDS run...', flush=True)
    p = FdsPipeline()
    checkpoint = p.load_checkpoint()
    last_autoindex = 4667586
    
    print(f'Fetching batch starting from {last_autoindex}...', flush=True)
    batch_ids = p.get_next_batch(last_autoindex, 2000)
    print(f'Got {len(batch_ids)} items.', flush=True)
    
    if not batch_ids:
        print('No data.')
        return
        
    print('Submitting to ThreadPoolExecutor...', flush=True)
    success = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_id = {executor.submit(p.process_item, idx, p.engine): idx for idx in batch_ids}
        
        for future in concurrent.futures.as_completed(future_to_id):
            idx = future_to_id[future]
            try:
                res = future.result(timeout=10) # 10s timeout to detect hang!
                success += 1
                if success % 10 == 0:
                    print(f'{success}/200 items processed...', flush=True)
            except concurrent.futures.TimeoutError:
                print(f'Item {idx} HUNG for >10s!', flush=True)
            except Exception as exc:
                print(f'Item {idx} failed: {exc}', flush=True)

if __name__ == '__main__':
    run_fds()
