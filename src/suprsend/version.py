try:
    from ._version import version as __version__
except ImportError:
    try:
        from importlib.metadata import PackageNotFoundError, version as _pkg_version
        __version__ = _pkg_version("suprsend-py-sdk")
    except PackageNotFoundError:
        __version__ = "0.0.0+unknown"
