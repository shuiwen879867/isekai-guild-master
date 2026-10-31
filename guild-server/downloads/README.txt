当前客户端：IsekaiGuildMaster-RenPy-3.2.0-live-cards-20261013-pc.zip
基于原 RenPy 项目的实时卡面修复版，保留 Alt 放大与既有服务器协议。
压缩包 177.5 MB；此前 RenPy PC 包 232.6 MB，减少 55.2 MB（23.7%）。
整包减少同时包括卡面优化及排除旧项目副本、开发资源。Godot 包保留为历史版本。

把客户端与服务器压缩包放在这个目录，对战器网站（默认端口 6680）会自动列出来。
The matchmaking website (default port 6680) lists every archive placed in this folder.

支持的扩展名 / supported extensions
    .zip  .7z  .rar  .tar.gz  .tgz  .exe  .msi  .dmg  .apk

文件名里含 "server"（或「服务器」）的会被标成「服务器包」，其余按「客户端」显示。
Files whose name contains "server" are labelled as server packages.

推荐做法
1. 在 Ren'Py 启动器里执行「构建发行版」，产物会出现在项目根目录的 dist/ 下。
2. 运行 `python tools/publish_client.py`，把 dist/ 里的压缩包复制到这里并打印下载链接。
   （也可以直接手动复制文件进来，或用 `--list` 查看当前对战器网站提供哪些文件。）
3. 浏览器打开 http://服务器地址:6667 的「下载」区域即可看到新文件。

注意：本目录里的非压缩包文件（例如这份说明）不会出现在网站上。
