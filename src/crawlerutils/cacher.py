import httpx
import yaml
import pathlib
import atexit
import hashlib
import typing
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed


from .config import DEFAULT_CACHE_DIRECTORY

class utils:
    @staticmethod
    def cal_sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def serialization(url: str, *args, **kwargs) -> str:
        return utils.cal_sha256(url.encode("utf-8"))


class CacheItemRef(typing.TypedDict):
    url: str  # origin_url
    args: list  # args
    kwargs: dict # kwargs


class CacheItem(typing.TypedDict):
    data: str  # hash
    ref: CacheItemRef # hash from


class Cacher:
    def __init__(self, cache_dir: pathlib.Path = DEFAULT_CACHE_DIRECTORY, proxy: str | None = None) -> None:
        self.memory_cache: dict[str, CacheItem]
        self.cache_directory: pathlib.Path = cache_dir.joinpath("cacher")
        self.blob_directory: pathlib.Path = cache_dir.joinpath("blob")
        self.proxy: str | None = proxy

    def fix_blob(self):
        if not self.blob_directory.is_dir():
            logger.info("skip fix blob directory")
        for f in self.blob_directory.iterdir():
            if f.is_file():
                if utils.cal_sha256(f.read_bytes()) != f.name:
                    logger.info(f"blob file {f} hash is uncorrect")
                    f.unlink()

    def register(self, proxy: str = None):
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        self.blob_directory.mkdir(parents=True, exist_ok=True)

        map_yaml = self.cache_directory.joinpath("mapping.yaml")
        if map_yaml.is_file():
            self.memory_cache = yaml.safe_load(map_yaml.open(encoding="utf-8"))
        else:
            self.memory_cache = {}

        # 注册退出回调
        atexit.register(self.__commit)


    def __commit(self):
        map_yaml = self.cache_directory.joinpath("mapping.yaml")
        logger.info(f"dump memory_cache to {map_yaml}")
        yaml.safe_dump(self.memory_cache, map_yaml.open("w", encoding="utf-8"))

    def __sha256_file(self, val: str) -> pathlib.Path:
        return self.blob_directory.joinpath(val)

    def __save_sha256_data(self, data: bytes) -> str:
        hashed = utils.cal_sha256(data)
        self.blob_directory.joinpath(hashed).write_bytes(data)
        return hashed


    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3))
    def __fetch(self, url: str, *args, **kwargs) -> pathlib.Path:
        cache_key: str = utils.serialization(url, *args, **kwargs)
        if cache_key in self.memory_cache:
            cache_item = self.memory_cache[cache_key]
            logger.info("cache hit, read data")
            data_file = self.__sha256_file(cache_item["data"])
            if data_file.is_file():
                return data_file
            # 缓存文件不存在
            logger.warning("cache hit, but cache file not exist")
        # 未命中缓存，或者缓存无效
        with httpx.Client(proxy=self.proxy) as client:
            resp = client.get(
                *args,
                **kwargs,
                url=url,
                follow_redirects=True,
            )
        resp.raise_for_status()
        data_hashed = self.__save_sha256_data(resp.content)
        cache_item: CacheItem = {
            "url": url,
            "data": data_hashed,
        }
        self.memory_cache[cache_key] = cache_item
        data_file = self.__sha256_file(data_hashed)
        if data_file.is_file():
            return data_file
        else:
            raise Exception("cannot fetch file")

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3))
    async def __afetch(self, url: str, *args, **kwargs) -> pathlib.Path:
        cache_key: str = utils.serialization(url, *args, **kwargs)
        if cache_key in self.memory_cache:
            cache_item = self.memory_cache[cache_key]
            logger.info("cache hit, read data")
            data_file = self.__sha256_file(cache_item["data"])
            if data_file.is_file():
                return data_file
            # 缓存文件不存在
            logger.warning("cache hit, but cache file not exist")
        # 未命中缓存，或者缓存无效
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            resp = await client.get(
                *args,
                **kwargs,
                url=url,
                follow_redirects=True,
            )
        resp.raise_for_status()
        data_hashed = self.__save_sha256_data(resp.content)
        cache_item: CacheItem = {
            "data": data_hashed,
            "ref": {
                "url": url,
                "args": args,
                "kwargs": kwargs,
            }
        }
        self.memory_cache[cache_key] = cache_item
        data_file = self.__sha256_file(data_hashed)
        if data_file.is_file():
            return data_file
        else:
            raise Exception("cannot fetch file")

    def download(self, url: str, file: pathlib.Path, *args, **kwargs):
        origin_file = self.__fetch(url=url, *args, **kwargs)
        try:
            file.unlink(missing_ok=True)
            file.hardlink_to(origin_file)
        except Exception:
            logger.warning("cannot create hard link, copy file")
            file.write_bytes(origin_file.read_bytes())

    def get(self, url: str, *args, **kwargs) -> bytes:
        return self.__fetch(url=url, *args, **kwargs).read_bytes()

    async def adownload(self, url: str, file: pathlib.Path, *args, **kwargs):
        origin_file = await self.__afetch(url=url, *args, **kwargs)
        try:
            file.unlink(missing_ok=True)
            file.hardlink_to(origin_file)
        except Exception:
            logger.warning("cannot create hard link, copy file")
            file.write_bytes(origin_file.read_bytes())

    async def aget(self, url: str, *args, **kwargs) -> bytes:
        return (await self.__afetch(url=url, *args, **kwargs)).read_bytes()
