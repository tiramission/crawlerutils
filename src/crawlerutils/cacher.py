import httpx
import yaml
import pathlib
import atexit
import hashlib
import typing
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed


from .config import CACHE_DIRECTORY


def cal_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class CacheItem(typing.TypedDict):
    url: str  # origin_url
    data: str  # hash


class Cacher:
    memory_cache: dict[str, CacheItem]
    cache_directory: pathlib.Path = CACHE_DIRECTORY.joinpath("cacher")
    blob_directory: pathlib.Path = CACHE_DIRECTORY.joinpath("blob")
    proxy: str | None = None

    @classmethod
    def fix_blob(cls):
        if not cls.blob_directory.is_dir():
            logger.info("skip fix blob directory")
        for f in cls.blob_directory.iterdir():
            if f.is_file():
                if cal_sha256(f.read_bytes()) != f.name:
                    logger.info(f"blob file {f} hash is uncorrect")
                    f.unlink()

    @classmethod
    def register(cls, proxy: str = None):
        cls.cache_directory.mkdir(parents=True, exist_ok=True)
        cls.blob_directory.mkdir(parents=True, exist_ok=True)
        cls.proxy = proxy

        map_yaml = cls.cache_directory.joinpath("mapping.yaml")
        if map_yaml.is_file():
            cls.memory_cache = yaml.safe_load(map_yaml.open(encoding="utf-8"))
        else:
            cls.memory_cache = {}

        # 注册退出回调
        atexit.register(cls.__commit)

    @classmethod
    def __commit(cls):
        map_yaml = cls.cache_directory.joinpath("mapping.yaml")
        logger.info(f"dump memory_cache to {map_yaml}")
        yaml.safe_dump(cls.memory_cache, map_yaml.open("w", encoding="utf-8"))

    @classmethod
    def __sha256_file(cls, val: str) -> pathlib.Path:
        return cls.blob_directory.joinpath(val)

    @classmethod
    def __save_sha256_data(cls, data: bytes) -> str:
        hashed = cal_sha256(data)
        cls.blob_directory.joinpath(hashed).write_bytes(data)
        return hashed

    @classmethod
    def serialization(cls, url: str, *args, **kwargs) -> str:
        return cal_sha256(url.encode("utf-8"))

    @classmethod
    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3))
    def __fetch(cls, url: str, *args, **kwargs) -> pathlib.Path:
        cache_key: str = cls.serialization(url, *args, **kwargs)
        if cache_key in cls.memory_cache:
            cache_item = cls.memory_cache[cache_key]
            logger.info("cache hit, read data")
            data_file = cls.__sha256_file(cache_item["data"])
            if data_file.is_file():
                return data_file
            # 缓存文件不存在
            logger.warning("cache hit, but cache file not exist")
        # 未命中缓存，或者缓存无效
        with httpx.Client(proxy=cls.proxy) as client:
            resp = client.get(
                *args,
                **kwargs,
                url=url,
                follow_redirects=True,
            )
        resp.raise_for_status()
        data_hashed = cls.__save_sha256_data(resp.content)
        cache_item: CacheItem = {
            "url": url,
            "data": data_hashed,
        }
        cls.memory_cache[cache_key] = cache_item
        data_file = cls.__sha256_file(data_hashed)
        if data_file.is_file():
            return data_file
        else:
            raise Exception("cannot fetch file")

    @classmethod
    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3))
    async def __afetch(cls, url: str, *args, **kwargs) -> pathlib.Path:
        cache_key: str = cls.serialization(url, *args, **kwargs)
        if cache_key in cls.memory_cache:
            cache_item = cls.memory_cache[cache_key]
            logger.info("cache hit, read data")
            data_file = cls.__sha256_file(cache_item["data"])
            if data_file.is_file():
                return data_file
            # 缓存文件不存在
            logger.warning("cache hit, but cache file not exist")
        # 未命中缓存，或者缓存无效
        async with httpx.AsyncClient(proxy=cls.proxy) as client:
            resp = await client.get(
                *args,
                **kwargs,
                url=url,
                follow_redirects=True,
            )
        resp.raise_for_status()
        data_hashed = cls.__save_sha256_data(resp.content)
        cache_item: CacheItem = {
            "url": url,
            "data": data_hashed,
        }
        cls.memory_cache[cache_key] = cache_item
        data_file = cls.__sha256_file(data_hashed)
        if data_file.is_file():
            return data_file
        else:
            raise Exception("cannot fetch file")

    @classmethod
    def download(cls, url: str, file: pathlib.Path, *args, **kwargs):
        origin_file = cls.__fetch(url=url, *args, **kwargs)
        try:
            file.unlink(missing_ok=True)
            file.hardlink_to(origin_file)
        except Exception:
            logger.warning("cannot create hard link, copy file")
            file.write_bytes(origin_file.read_bytes())

    @classmethod
    def get(cls, url: str, *args, **kwargs) -> bytes:
        return cls.__fetch(url=url, *args, **kwargs).read_bytes()

    @classmethod
    async def adownload(cls, url: str, file: pathlib.Path, *args, **kwargs):
        origin_file = await cls.__afetch(url=url, *args, **kwargs)
        try:
            file.unlink(missing_ok=True)
            file.hardlink_to(origin_file)
        except Exception:
            logger.warning("cannot create hard link, copy file")
            file.write_bytes(origin_file.read_bytes())

    @classmethod
    async def aget(cls, url: str, *args, **kwargs) -> bytes:
        return (await cls.__afetch(url=url, *args, **kwargs)).read_bytes()
