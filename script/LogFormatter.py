import os

class LogFormatter:
    def __init__(self, project=None):
        self._project_root = project
        self._pid = os.getpid()
        pass

    def __call__(self, message):
        return f' PID:{self._pid} [{self._project_root}] {message}'