
import json
import time
import importlib
import multiprocessing
import os
import sys

# Ensure parent directory is in sys.path so 'etl_core' can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

CONFIG_FILE = os.path.join(current_dir, "scheduler_config.json")

def run_pipeline(pipeline_config):
    """
    Worker process function to run a single pipeline.
    """
    name = pipeline_config['name']
    module_name = pipeline_config['module']
    class_name = pipeline_config['class']
    interval = pipeline_config.get('interval_seconds', 60)
    batch_size = pipeline_config.get('batch_size', 200)
    workers = pipeline_config.get('workers', 10)
    checkpoint_file = pipeline_config.get('checkpoint_file') 
    start_autoindex = pipeline_config.get('start_autoindex')
    
    print(f"[Scheduler] 🚀 Starting {name} process...")
    
    try:
        # Dynamically import module and class
        module = importlib.import_module(module_name)
        PipelineClass = getattr(module, class_name)
        
        # Instantiate
        # Note: We assume the pipeline class __init__ accepts checkpoint_file if provided
        if checkpoint_file:
            pipeline = PipelineClass(batch_size=batch_size, workers=workers, checkpoint_file=checkpoint_file)
        else:
             pipeline = PipelineClass(batch_size=batch_size, workers=workers)
        
        # Run loop
        pipeline.run(resume=True, loop_interval=interval, start_autoindex=start_autoindex)
        
    except Exception as e:
        print(f"[Scheduler] 💥 {name} process crashed: {e}")
        time.sleep(10) # Prevent tight crash loop

def main():
    print(f"[Scheduler] Loading configuration from {CONFIG_FILE}...")
    if not os.path.exists(CONFIG_FILE):
        print(f"[Scheduler] ❌ Config file {CONFIG_FILE} not found!")
        return

    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    processes = []
    
    for p_conf in config.get('pipelines', []):
        if p_conf.get('enabled', False):
            p = multiprocessing.Process(target=run_pipeline, args=(p_conf,))
            p.start()
            processes.append(p)
            print(f"[Scheduler] Launched {p_conf['name']} (PID: {p.pid})")

    try:
        # Monitor processes
        while True:
            time.sleep(5)
            for p in processes:
                if not p.is_alive():
                    print(f"[Scheduler] ⚠️ Process {p.pid} died. (Restart logic could be implemented here)")
    except KeyboardInterrupt:
        print("\n[Scheduler] 🛑 Stopping all processes...")
        for p in processes:
            p.terminate()
            p.join()
        print("[Scheduler] Bye.")

if __name__ == "__main__":
    main()
