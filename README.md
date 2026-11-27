# tvbox — 自用电视配置（自建仓库）

这个仓库只放我自己在用的 TVBox 配置：**13 个精筛点播站** + **央视/卫视直播（只留备选线路）**，另附一个多仓入口用来切饭太硬。
所有地址都是本机逐条实测过的，判据写在文末。

## 怎么用（电视端填这一个地址）

```
https://cdn.jsdelivr.net/gh/wlongdan/tvbox@main/config.json
```

备用（jsDelivr 被墙或抽风时换，永远最新）：

```
https://raw.githubusercontent.com/wlongdan/tvbox/main/config.json
```

TVBox 操作：设置 → 配置地址 → 粘贴 → 确定 → 回首页刷新。
影视仓/肥猫/影视TV 同理，找「配置地址 / 接口」填这一行。

## 文件说明

| 文件 | 内容 |
| --- | --- |
| `config.json` | 总配置：13 个点播站 + 3 组直播（电视上就填这个） |
| `live.m3u` | 直播·**只留备选线路** 50 频道（46 个 1080p + 4 个 720p，全部实拉切片验证） |
| `live-fast.m3u` | 直播·低延迟 4 条（切片 ≤8 秒，换台最快） |
| `live-full.m3u` | 直播·全部线路 155 条（备选全挂时的后备池） |
| `多仓.json` | 多仓入口：自用 13 站 + 饭太硬官方仓（TV 里可切换） |

## 点播源（13 站，全部直连采集，按响应快慢排序）

| # | 站点 | 接口 | 列表 | 详情 |
| --- | --- | --- | --- | --- |
| 1 | 巨量资源 | `https://api.juliang.live/api/provide/vod` | 0.66s | 1.12s |
| 2 | 360资源 | `https://360zy.com/api.php/provide/vod` | 0.80s | 0.98s |
| 3 | 精品资源 | `http://www.jingpinx.com/api.php/provide/vod` | 0.79s | 1.16s |
| 4 | 爱奇艺资源 | `https://www.iqiyizyapi.com/api.php/provide/vod` | 0.87s | 1.37s |
| 5 | 电影天堂 | `https://dyttzy.tv/api.php/provide/vod` | 0.92s | 1.94s |
| 6 | 番茄资源 | `https://fqzy.me/api.php/provide/vod` | 1.25s | 1.82s |
| 7 | 无尽资源 | `https://api.wujinapi.com/api.php/provide/vod` | 0.66s | 3.93s |
| 8 | 墨斗资源 | `https://www.mdzyapi.com/api.php/provide/vod` | 1.56s | 2.92s |
| 9 | 闪电资源 | `https://sdzyapi.com/api.php/provide/vod` | 0.89s | 5.60s |
| 10 | 10010888 | `https://cj.10010888.xyz/api.php/provide/vod` | 1.62s | 4.83s |
| 11 | 荣耀资源 | `https://cj.rytvapi.com/api.php/provide/vod` | 3.65s | 1.50s |
| 12 | 豪华资源 | `https://hhzyapi.com/api.php/provide/vod` | 4.17s | 2.79s |
| 13 | 红牛资源 | `https://www.hongniuzy2.com/api.php/provide/vod` | 4.73s | 3.60s |

入选门槛（缺一条都淘汰）：

- **直连采集（type=1）**，不依赖 jar/spider —— 壳子的 jar 版本一错、或站点后端换接口，spider 站就整片黑屏，这是「很多片播不了」的头号原因。
- 播放地址**不带时效 token**（`auth=` / `token=` / `expire=` / `sign=`），带签名的过几天整站作废。
- 播放清单**没有 CUE-OUT / CUE-IN 广告插播标记**。
- 列表与详情接口秒级响应，切片时长不超 20 秒。
- 13 站全部**支持关键词搜索**（用「庆余年」实测有结果），这是「片子搜不到」的关键，不靠堆数量。

## 为什么饭太硬没并进主配置

饭太硬（`http://饭太硬.top/tv`）的资源全是 **spider 类（type=3）**，必须配它自己的 `fty.jar`。
我把它的 2401 版配置和 jar 镜像下来试过：**jsDelivr 对所有 `.jar` 一律 403**（CDN 屏蔽该扩展名），raw 通道在国内又常被挡，jar 没法稳定托管。
所以改成**多仓入口**：填 `多仓.json` 的地址后，TVBox 会多出一个「饭太硬官方仓」，由电视直连它自己的服务器取 jar，成功率最高，也不会把主配置拖挂。

```
https://cdn.jsdelivr.net/gh/wlongdan/tvbox@main/多仓.json
```

## 直播源（只留备选线路）

50 个频道：CCTV-1/2/3/4/5/5+/6/7/8/9/10/11/12/13/14/15/16/17、CGTN，以及北京、东方、江苏、浙江、湖南、湖北、广东、深圳、安徽、山东、天津、重庆、四川、河南、河北、辽宁、吉林、黑龙江、东南、江西、广西、贵州、云南、陕西、甘肃、青海、宁夏、新疆、内蒙古、西藏、三沙等卫视。

做过的调整：

- **默认只留「备」线路**，实测备选比首选稳（首选的 `107.150.60.122`/`38.75.136.137` 经常抽风）。
- 没有备选、或备选拉不动的频道（CCTV-2、14、15、16、湖南卫视）用首选兜底，并在说明里标注。
- 海南卫视：唯一的备选线路切片下载失败，已从清单移出，宁缺不假。
- CGTN 换成 `0472.org` 的 720p 线路（该地址是嵌套多码率清单，需进两层才取到真实切片）。
- 分辨率不是猜标签：逐条拉切片解 TS 的 H.264/HEVC SPS 读真实画面尺寸 → 46 个 1920×1072、4 个 1280×720。

## 更新与自查

- jsDelivr 缓存最长约 12 小时；急用走 raw 地址，或换成锁版本地址（`@<commit sha>`）。
- 加频道：按 `#EXTINF:-1 tvg-name="频道名" group-title="央视",频道名` 追加一行地址。
- 不写死 EPG/台标，避免第三方 EPG 挂掉导致进直播页卡死。
- 某站失效就按同一门槛重测替换：列表 200 + 播放地址无签名 + 清单无广告标记 + 详情秒级。

## 说明

内容接口来自公开可访问的采集站清单，本仓库只做「筛选 + 结构整理 + 实测记录」，不存储、不分发任何影视文件。
