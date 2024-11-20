from crawlerutils import Cacher
from pathlib import Path
from loguru import logger
import pytest

logger.remove()
root = Path(__file__).parent.parent.joinpath(".cache")


# Cacher.register(proxy="http://192.168.30.15:7890")
c = Cacher(cache_dir=root.joinpath("storage"))
c.register()
c.fix_blob()


@pytest.mark.asyncio(loop_scope="module")
async def test_async_cacher():
    result_file = root.joinpath("temps").joinpath("result.html")
    result_file.parent.mkdir(parents=True, exist_ok=True)
    await c.adownload(url="https://www.google.com", file=result_file)
    assert result_file.is_file()
    assert (await c.aget("https://www.baidu.com")) == result_file.read_bytes()
    result_file.unlink()


def test_cacher():
    result_file = root.joinpath("temps").joinpath("result.html")
    result_file.parent.mkdir(parents=True, exist_ok=True)
    c.download(url="https://www.google.com", file=result_file)
    assert result_file.is_file()
    assert c.get("https://www.baidu.com") == result_file.read_bytes()
    result_file.unlink()
