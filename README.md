# tvbox — 自用电视配置（自建仓库）

这个仓库里只放我自己在用的 TVBox 配置：一套**精筛点播源**（20 站）+ 一套**央视/卫视直播源**（3 份清单）。
所有地址都由本机逐条实测过，判断依据写在文末，源不在多而在于稳。

## 怎么用（电视端填这一个地址）

```
https://cdn.jsdelivr.net/gh/wlongdan/tvbox@main/config.json
```

备用地址（jsDelivr 被墙或抽风时换这个）：

```
https://raw.githubusercontent.com/wlongdan/tvbox/main/config.json
```

TVBox 操作：设置 → 配置地址 → 粘贴上面任一地址 → 确定 → 回家刷新。
影视仓/肥猫/影视TV 等同类壳子同理，找「配置地址 / 接口」填这一行即可。

## 文件说明

| 文件 | 内容 |
| --- | --- |
| `config.json` | 总配置：20 个点播站 + 3 组直播（电视上就填这个） |
| `live.m3u` | 直播·高清优先 97 条（52 个频道，每频道首选 1080p + 一台不同服务器备选） |
| `live-fast.m3u` | 直播·低延迟 17 条（切片 ≤6 秒，换台最快） |
| `live-full.m3u` | 直播·全部线路 155 条（首选失效时的后备池） |

## 点播源（20 站，全部直连采集，按响应快慢排序）

| # | 站点 | 接口 | 列表 | 详情 | 搜索 |
| --- | --- | --- | --- | --- | --- |
| 1 | 巨量资源 | `https://api.juliang.live/api/provide/vod` | 0.66s | 1.12s | 支持 |
| 2 | 360资源 | `https://360zy.com/api.php/provide/vod` | 0.80s | 0.98s | 支持 |
| 3 | 精品资源 | `http://www.jingpinx.com/api.php/provide/vod` | 0.79s | 1.16s | 支持 |
| 4 | 爱奇艺资源 | `https://www.iqiyizyapi.com/api.php/provide/vod` | 0.87s | 1.37s | 支持 |
| 5 | 9号资源 | `https://fhapi9.com/api.php/provide/vod` | 0.69s | 2.03s | 支持 |
| 6 | 电影天堂 | `https://dyttzy.tv/api.php/provide/vod` | 0.92s | 1.94s | 支持 |
| 7 | 番茄资源 | `https://fqzy.me/api.php/provide/vod` | 1.25s | 1.82s | 支持 |
| 8 | 无尽资源 | `https://api.wujinapi.com/api.php/provide/vod` | 0.66s | 3.93s | 支持 |
| 9 | 樱花资源 | `https://yhzy.cc/api.php/provide/vod` | 1.43s | 2.37s | 支持 |
| 10 | 极速资源 | `https://jszyapi.com/api.php/provide/vod` | 1.28s | 3.62s | 支持 |
| 11 | 墨斗资源 | `https://www.mdzyapi.com/api.php/provide/vod` | 1.56s | 2.92s | 支持 |
| 12 | 闪电资源 | `https://sdzyapi.com/api.php/provide/vod` | 0.89s | 5.60s | 支持 |
| 13 | 10010888 | `https://cj.10010888.xyz/api.php/provide/vod` | 1.62s | 4.83s | 支持 |
| 14 | 荣耀资源 | `https://cj.rytvapi.com/api.php/provide/vod` | 3.65s | 1.50s | 支持 |
| 15 | 玉兔资源 | `https://apiyutu.com/api.php/provide/vod` | 2.10s | 6.79s | 支持 |
| 16 | U酷资源 | `https://api.ukuapi88.com/api.php/provide/vod` | 3.50s | 4.54s | 支持 |
| 17 | 豪华资源 | `https://hhzyapi.com/api.php/provide/vod` | 4.17s | 2.79s | 支持 |
| 18 | 红牛资源 | `https://www.hongniuzy2.com/api.php/provide/vod` | 4.73s | 3.60s | 支持 |
| 19 | 光速资源 | `https://api.guangsuapi.com/api.php/provide/vod` | 4.60s | 6.88s | 支持 |
| 20 | 金鹰资源 | `https://jyzyapi.com/api.php/provide/vod` | 5.94s | 4.89s | 支持 |

为什么只用这 20 个（364 个候选里筛出来的）：

- **直连采集（type=1）**，不依赖 jar/spider。壳子和 jar 版本一错、或站点后端换接口，spider 站点就整片黑屏，这是"很多片播不了"的头号原因。
- 播放地址**不带时效 token**（`auth=` / `token=` / `expire=` / `sign=`），带签名的地址过几天整站作废。
- 播放清单里**没有 CUE-OUT / CUE-IN 广告插播标记**。
- 列表与详情接口都在秒级；切片时长异常（>20 秒）的站淘汰。
- 20 个站全部**支持关键词搜索**（用"庆余年"实测有结果），这是解决"片子搜不到"的关键，不是靠堆数量。

本轮新增 12 站的来源：GitHub 公开 TVBox 配置文件里抓了 3662 条接口字符串 → 去重 382 个 → 排除重复/成人/前轮淘汰剩 364 个 → 46 个列表可用 → 31 个详情+播放通过 → 12 个入选。
淘汰的典型：豆豆魔方/牛牛（列表 7~9s 或搜索无结果）、量子（详情 17.8s）、鸭鸭（详情 13.4s）、速播（播放地址拉不到）、CK影视（分类接口拉不出）、最大资源（域名时通时断）。

## 直播源

52 个频道：CCTV-1/2/3/4/5/5+/6/7/8/9/10/11/12/13/14/15/17、CGTN、CETV 系列，以及北京、上海东方、江苏、浙江、湖南、湖北、广东、深圳、安徽、山东、天津、重庆、四川、河南、河北、辽宁、吉林、黑龙江、福建东南、江西、广西、贵州、云南、陕西、甘肃、青海、宁夏、新疆、内蒙古、西藏、海南、三沙等省级卫视。

清晰度不是看标签猜的：M3U8 里普遍没有 `RESOLUTION` 字段，所以逐条拉切片、解 TS 里的 H.264/HEVC SPS 读真实分辨率。结果 50 个频道是 1920×1072（1080p），个别源是 720p，已剔除 608×1008、16×128、16×32 这类残废流。4K 线路（江苏 8.138.7.223）解码压力大，只留作备选。

排序规则：真实分辨率 → 切片时长 → 首字节耗时；每频道留「首选 + 一台不同服务器备选」，避免同一台机器挂掉时全频道同时黑。

## 更新与自查

- 仓库改了以后 jsDelivr 有缓存，最长约 12 小时；急用就换 `raw.githubusercontent.com` 那条，或者 URL 后面加 `?t=` 时间戳。
- 想自己加频道：按 `live.m3u` 里 `#EXTINF:-1 tvg-name="频道名" group-title="央视",频道名` 的格式追加一行地址即可。
- 配置里不写死 EPG 和台标，避免第三方 EPG 挂掉导致进直播页面卡住。
- 接口失效很常见，按上面同一套门槛重测替换即可（判据：列表 200、播放地址无签名、清单无广告标记）。

## 说明

内容接口来自公开可访问的采集站清单，本仓库只做「筛选 + 结构整理 + 实测记录」，不存储、不分发任何影视文件。
