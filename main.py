from crawlerutils import cacher


if __name__ == "__main__":
    cacher.init()
    print(cacher.httpx_get("https://www.baidu.com"))
