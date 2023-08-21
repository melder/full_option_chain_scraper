from config import config  # pylint: disable=wrong-import-order
import multiprocessing
import os
import sys


def start_worker():
    if sys.platform != "darwin":
        os.system("rq worker --with-scheduler -b")
    else:
        os.system(
            "OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES rq worker --with-scheduler -b"
        )


def main():
    num_workers = config.conf.workers  # Set the number of concurrent workers
    processes = []

    # Start the worker processes
    for _ in range(num_workers):
        process = multiprocessing.Process(target=start_worker)
        process.start()
        processes.append(process)

    # Wait for all processes to finish
    for process in processes:
        process.join()


if __name__ == "__main__":
    if sys.platform != "darwin":
        multiprocessing.set_start_method("spawn")
    main()
