import pathlib
import tempfile

CACHE_DIRECTORY: pathlib.Path = pathlib.Path(tempfile.gettempdir()).joinpath(
    "crawlerutils"
)
