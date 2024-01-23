import os
import signal
import json
import threading
import time
from queue import Queue
from datetime import datetime



class JSONlogger:

    worker_thread = None
    eventCounter = {}


    def init(fileName="log", filePath="./"):
        if JSONlogger.worker_thread is not None:
            raise Exception("JSONlogger: init() cannot be called more than once!")

        JSONlogger.queue = Queue()
        JSONlogger.worker_thread = threading.Thread(target=JSONlogger._file_writer, args=(filePath+fileName+".json",))
        JSONlogger.worker_thread.start()


    def close():
        print("[JSONlogger] Closing...")
        # Put the event counter dictionary at the end
        record = {"total": JSONlogger.eventCounter}
        JSONlogger.queue.put(record)
        # Signal the worker thread to exit
        JSONlogger.queue.put(None)
        # Wait for the worker thread to finish
        JSONlogger.worker_thread.join()
        JSONlogger.worker_thread = None


    def _flush_file(file):
        file.flush()
        os.fsync(file.fileno())



    def _file_writer(file):
        with open(file, "x") as f:
            f.write("[\n")
            JSONlogger._flush_file(f)

            firstRecord = True
            
            while True:
                # Block and wait for data in the queue
                data = JSONlogger.queue.get()
                if data is None:
                    break  # Exit the thread when a None is encountered
                
                # Write a delimiter and the data record
                if firstRecord:
                    firstRecord = False
                else:
                    f.write(",\n")
                f.write("\t")
                

                f.write(json.dumps(data, sort_keys=True))
                JSONlogger._flush_file(f)

            # End the JSON
            f.write("\n]")
            JSONlogger._flush_file(f)

    
    def _put_record_to_queue(rec):
        JSONlogger.queue.put(rec)


    def event(name, timestamp, **kwargs):
        record = {
            "sysNanos": time.perf_counter_ns(),
            "sysTime": str(datetime.now()),
            "eventTime": timestamp,
            "event": name,
        }
        
        if bool(kwargs): # True if the dictionary is not empty
            record["~data"] = kwargs

        JSONlogger.eventCounter[name] = 1 if JSONlogger.eventCounter.get(name) == None else JSONlogger.eventCounter[name]+1
        
        JSONlogger._put_record_to_queue(record)



# Example usage:
if __name__ == "__main__":

    JSONlogger.init()

    JSONlogger.event(name="test1", timestamp=0)
    JSONlogger.event(name="test1", timestamp=1, data1=1, data2=2)

    time.sleep(1)

    JSONlogger.event(name="test2", timestamp=10)

    # The API must be closed when done to ensure the worker thread exits gracefully
    JSONlogger.close()