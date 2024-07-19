from crawlerutils import Cacher
from pathlib import Path
from loguru import logger

logger.remove()
root = Path(__file__).parent.parent

def test_cacher():
    Cacher.register()
    result_file = root.joinpath("temps").joinpath("result.html")
    result_file.parent.mkdir(parents=True, exist_ok=True)
    Cacher.download(url="https://www.google.com", file=result_file)
    assert result_file.is_file()
    assert Cacher.get("https://www.google.com") == result_file.read_bytes()
    result_file.unlink()