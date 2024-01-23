# Source: https://stackoverflow.com/a/40579742

import threading
import datetime


class RSemaphore(object):

    '''A counting Semaphore which allows threads to reenter.'''

    def __init__(self, value=1):
        self.local = threading.local()
        self.sem = threading.Semaphore(value)


    def acquire(self):
        if not getattr(self.local, 'lock_level', 0):
            # We do not yet have the lock, acquire it.
            self.sem.acquire()
            self.local.lock_time = datetime.datetime.utcnow()
            self.local.lock_level = 1
        else:
            # We already have the lock, just increment it due to the recursive call.
            self.local.lock_level += 1


    def release(self):
        if getattr(self.local, 'lock_level', 0) < 1:
            raise Exception("Trying to release a released lock.")

        self.local.lock_level -= 1
        if self.local.lock_level == 0:
            self.sem.release()


    __enter__ = acquire

    def __exit__(self, t, v, tb):
        self.release()
