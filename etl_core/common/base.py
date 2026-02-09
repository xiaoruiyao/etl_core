
import abc
import json
import os
import time
import concurrent.futures
from datetime import datetime
from sqlalchemy import text
from .db import create_db_engine

class BaseEtlPipeline(abc.ABC):
    def __init__(self, name, checkpoint_file, batch_size=200, workers=10, limit=None):
        self.name = name
        self.checkpoint_file = checkpoint_file
        self.batch_size = batch_size
        self.workers = workers
        self.limit = limit
        self.engine = create_db_engine(pool_size=workers+5)
        self.stop_event = False

    def load_checkpoint(self):
        """Load checkpoint from file"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    print(f"[{self.name}] 📌 Loaded Checkpoint: autoindex={data.get('last_autoindex')}, time={data.get('last_time')}")
                    return data
            except Exception as e:
                print(f"[{self.name}] ⚠️ Failed to load checkpoint: {e}")
        return {"last_autoindex": 0, "last_time": None, "success_count": 0, "fail_count": 0}

    def save_checkpoint(self, autoindex, success_count=0, fail_count=0):
        """Save checkpoint to file"""
        data = {
            "last_autoindex": autoindex,
            "last_time": datetime.now().isoformat(),
            "success_count": success_count,
            "fail_count": fail_count
        }
        with open(self.checkpoint_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"[{self.name}] 💾 Saved Checkpoint: autoindex={autoindex}")

    @abc.abstractmethod
    def get_next_batch(self, last_autoindex, batch_size):
        """
        Return list of IDs to process.
        Must be implemented by subclass.
        """
        pass

    @abc.abstractmethod
    def process_item(self, item_id, engine):
        """
        Process a single item.
        Must be implemented by subclass.
        Returns True on success, False on failure.
        """
        pass

    def get_item_offset(self, item):
        """
        Extract the offset/ID from the item.
        Default: return item (assumes item IS the offset).
        Override in subclass if item is a tuple/dict.
        """
        return item

    def run(self, resume=True, loop_interval=None, start_autoindex=None):
        """
        Main execution loop.
        :param resume: If True, resume from checkpoint.
        :param loop_interval: If set (int seconds), run in a continuous loop waiting for new data.
        :param start_autoindex: Force start from specific index (overrides checkpoint if resume=False).
        """
        checkpoint = self.load_checkpoint()
        
        last_autoindex = 0
        if resume and checkpoint.get("last_autoindex"):
            last_autoindex = checkpoint["last_autoindex"]
        elif start_autoindex is not None:
             last_autoindex = start_autoindex

        success = checkpoint.get("success_count", 0) if resume else 0
        failed = checkpoint.get("fail_count", 0) if resume else 0
        total_processed_session = 0
        
        print(f"[{self.name}] 🚀 Starting Pipeline. Start Index: {last_autoindex}, Workers: {self.workers}, Loop: {loop_interval}s")

        while not self.stop_event:
            # Check limit
            if self.limit and total_processed_session >= self.limit:
                print(f"[{self.name}] 🛑 Reached session limit ({self.limit}). Stopping.")
                break

            # 1. Get Batch
            try:
                batch_ids = self.get_next_batch(last_autoindex, self.batch_size)
            except Exception as e:
                 print(f"[{self.name}] 💥 Error fetching batch: {e}")
                 time.sleep(5)
                 continue

            if not batch_ids:
                if loop_interval:
                    print(f"[{self.name}] 💤 No new data. Sleeping {loop_interval}s...")
                    time.sleep(loop_interval)
                    continue
                else:
                    print(f"[{self.name}] ✅ No more data. Finished.")
                    break
            
            # print(f"[{self.name}] 📥 Batch: {len(batch_ids)} items ({batch_ids[0]} -> {batch_ids[-1]})")
            
            # 2. Process Batch Parallel
            batch_success = 0
            batch_failed = 0
            max_id_in_batch = last_autoindex
            
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
                future_to_id = {executor.submit(self.process_item, idx, self.engine): idx for idx in batch_ids}
                
                for future in concurrent.futures.as_completed(future_to_id):
                    idx = future_to_id[future]
                    offset_val = self.get_item_offset(idx)
                    try:
                        result = future.result()
                        if result:
                            batch_success += 1
                        else:
                            batch_failed += 1
                    except Exception as exc:
                        print(f"[{self.name}] 💥 Item {idx} execution failed: {exc}")
                        batch_failed += 1
                    
                    if offset_val > max_id_in_batch:
                        max_id_in_batch = offset_val
            
            end_time = time.time()
            duration = end_time - start_time
            speed = len(batch_ids) / duration if duration > 0 else 0
            
            # 3. Update State
            success += batch_success
            failed += batch_failed
            total_processed_session += len(batch_ids)
            last_autoindex = max_id_in_batch
            
            # 4. Save Checkpoint
            self.save_checkpoint(last_autoindex, success, failed)
            print(f"[{self.name}] ⏱️ Batch Done. Time: {duration:.2f}s, Speed: {speed:.1f} rec/s. Total Success: {success}")

