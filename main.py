from crawlerutils.cacher import Cacher
import pathlib

if __name__ == "__main__":
    Cacher.register()
    Cacher.download(
        url="https://www.baidu.com",
        file=pathlib.Path("./rel.html"),
    )
    Cacher.fix_blob()
