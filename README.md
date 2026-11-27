# tvbox — 自用电视配置（自建仓库）

只放自己在用的 TVBox 配置：**11 个精筛点播站** + **央视/卫视直播 51 频道（每台 2-3 条线路，卡了能切）**。

## 怎么用（电视端填这一个地址）

```
https://cdn.jsdelivr.net/gh/wlongdan/tvbox@99491f1a49c5703ef7e41011f38ea442e4f5bbe7/tv.json
```

CDN 版（国内节点更快，内容与上面完全一致，永久固定）：

```
https://cdn.jsdelivr.net/gh/wlongdan/tvbox@99491f1a49c5703ef7e41011f38ea442e4f5bbe7/tv.json
```

备用（raw 被墙时换）：

```
https://cdn.jsdelivr.net/gh/wlongdan/tvbox@99491f1a49c5703ef7e41011f38ea442e4f5bbe7/tv.json
```

TVBox：设置 → 配置地址 → 粘贴 → 确定 → 回首页刷新。影视仓 / 影视TV / 蜂蜜 同理，找「配置地址」填这一行。

raw 备用：

```
https://raw.githubusercontent.com/wlongdan/tvbox/main/config.json
```

## 文件说明

| 文件 | 内容 |
| --- | --- |
| `tv.json` | 主入口：11 个点播站 + 2 组直播 |
| `config.json` | 与 `tv.json` 相同，raw 备用通道 |
| `live.m3u` | 直播主清单：**51 频道 / 144 条线路**，同台 2-3 条不同服务器，卡了直接切下一条 |
| `live-full.m3u` | 全部线路池（155 条），主清单里某台全挂了再来这里找 |

## 点播源（11 站，全部直连采集、支持搜索）

| # | 站点 | 接口 |
| --- | --- | --- |
| 1 | 巨量资源 | `https://api.juliang.live/api/provide/vod` |
| 2 | 360资源 | `https://360zy.com/api.php/provide/vod` |
| 3 | 爱奇艺资源 | `https://www.iqiyizyapi.com/api.php/provide/vod` |
| 4 | 电影天堂 | `https://dyttzy.tv/api.php/provide/vod` |
| 5 | 无尽资源 | `https://api.wujinapi.com/api.php/provide/vod` |
| 6 | 墨斗资源 | `https://www.mdzyapi.com/api.php/provide/vod` |
| 7 | 闪电资源 | `https://sdzyapi.com/api.php/provide/vod` |
| 8 | 10010888 | `https://cj.10010888.xyz/api.php/provide/vod` |
| 9 | 荣耀资源 | `https://cj.rytvapi.com/api.php/provide/vod` |
| 10 | 豪华资源 | `https://hhzyapi.com/api.php/provide/vod` |
| 11 | 红牛资源 | `https://www.hongniuzy2.com/api.php/provide/vod` |

入选门槛（缺一条都淘汰）：

- **直连采集（type=1）**，不依赖 jar。壳子的 jar 版本一错或站点换后端，spider 站就整片黑屏。
- 播放地址**不带时效 token**（`auth=` / `token=` / `expire=` / `sign=`），带签名的过几天整站作废。
- 播放清单**没有 CUE-OUT / CUE-IN 广告插播**，不走「前三分钟能放、后面全是广告」那种源。
- 列表与详情秒级响应，切片不超 20 秒。
- 用「庆余年」实测**搜索有结果**——电视上找不到片，八成就是这一步废了。

已剔除的站（不再出现）：樱花 `yhzy.cc`、急速 `jszyapi.com`、玉兔 `apiyutu.com`、U酷 `api.ukuapi88.com`、光速 `api.guangsuapi.com`、金鹰 `jyzyapi.com`、精品 `jingpinx.com`、番茄 `fqzy.me`，以及饭太硬整套 spider 资源（依赖 jar，CDN 对 `.jar` 一律 403，接进来会整片黑屏）。

## 直播源：51 频道，每台 2-3 条线路

央视 19 个：CCTV-1~17、CCTV-5+、CGTN。卫视 32 个：北京、东方、江苏、浙江、湖南、湖北、广东、深圳、安徽、山东、天津、重庆、四川、河南、河北、辽宁、吉林、黑龙江、东南、江西、广西、贵州、云南、陕西、甘肃、青海、宁夏、新疆、内蒙古、西藏、海南、山西。

怎么挑的：

- **每台 2-3 条，且尽量落在不同服务器**，一条卡了切下一条，不用退回列表。
- 优先官方 / 播控 CDN 的线路（首包 <1 秒），其次才是 IPTV 镜像台。
- 已剔除：16×16 的假高清（`jsws4k`）、4K 但码率跟不上的（河北 `live101`）。
- 个别台全网只有一个源（CGTN 只有 0472 一条主源 + 一条镜像变体），已如实标注。

## 更新与自查

- 改完仓库，raw 立即生效；jsDelivr 走锁版本号（`@<commit sha>`）。
- 加频道：`#EXTINF:-1 tvg-name="频道名" group-title="央视",频道名·线路1` 后面跟地址，同台再加「·线路2」。
- 某台卡：先在 `live.m3u` 里切该台的线路2/3，全挂再去 `live-full.m3u` 找同名。
- 不写死 EPG/台标，避免第三方 EPG 挂掉导致进直播页卡死。

## 说明

内容接口来自公开可访问的采集站清单，本仓库只做「筛选 + 结构整理 + 实测记录」，不存储、不分发任何影视文件。
