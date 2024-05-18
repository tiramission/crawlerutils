import json
import tempfile
import pathlib
import loguru
import httpx
import hashlib
import typing


class CacheItem(typing.TypedDict):
    url: str
    data_hash: str


__cache_dir: pathlib.Path = None
__proxy: str = None
__dataset: dict[str, CacheItem] = {}


def init(cache_dir: pathlib.Path = None, proxy: str = None):
    if cache_dir is None:
        cache_dir = pathlib.Path(tempfile.gettempdir()) / "crawlerutils"
    global __cache_dir, __proxy, __dataset
    __cache_dir = cache_dir
    __cache_dir.mkdir(parents=True, exist_ok=True)
    loguru.logger.debug(f"Cache dir: {__cache_dir}")
    __proxy = proxy
    loguru.logger.debug(f"Proxy: {__proxy}")
    mapfile = get_cache_mapping()
    if mapfile.exists():
        __dataset = json.loads(mapfile.read_bytes())


def get_cache_dir() -> pathlib.Path:
    if __cache_dir is None:
        raise Exception("Cache dir not initialized")
    if not __cache_dir.exists():
        __cache_dir.mkdir(parents=True)
    return __cache_dir


def get_cache_mapping() -> pathlib.Path:
    return get_cache_dir() / "mapping.json"


def get_proxies() -> dict | None:
    if __proxy is None:
        return None
    else:
        return {"http://": __proxy, "https://": __proxy}


def cal_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_hashfile(hash_value: str) -> pathlib.Path | None:
    f = get_cache_dir().joinpath(hash_value)
    if f.exists():
        return f
    return None


def save_hashfile(data: bytes) -> tuple[str, pathlib.Path]:
    hash_value = cal_sha256(data)
    f = get_cache_dir().joinpath(hash_value)
    f.write_bytes(data)
    return hash_value, f


def commit():
    get_cache_mapping().write_text(
        json.dumps(__dataset, ensure_ascii=False),
        encoding="utf-8",
    )


def httpx_get(url: str) -> pathlib.Path:
    _cache_key = cal_sha256(url.encode())
    if _cache_key in __dataset:
        loguru.logger.debug(f"Cache hit: {url}")
        cache_item = __dataset[_cache_key]
        data_hash = cache_item["data_hash"]
        cache_file = find_hashfile(data_hash)
        if cache_file is not None:
            return cache_file
        loguru.logger.debug(f"Cache hit, but file miss: {url} -> {data_hash}")
    # 否则获取数据
    resp = httpx.get(
        url=url, proxies=get_proxies(), follow_redirects=True, verify=False
    )
    resp.raise_for_status()
    data_hash, cache_file = save_hashfile(resp.content)
    __dataset[_cache_key] = {"url": url, "data_hash": data_hash}
    commit()
    return cache_file
