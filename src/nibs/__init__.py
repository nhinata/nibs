from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nibs")
except PackageNotFoundError:  # running from a checkout that was never installed
    __version__ = "unknown"
