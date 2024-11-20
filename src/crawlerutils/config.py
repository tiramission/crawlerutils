import pathlib
import tempfile

DEFAULT_CACHE_DIRECTORY: pathlib.Path = pathlib.Path(tempfile.gettempdir()).joinpath(
    "crawlerutils"
)
