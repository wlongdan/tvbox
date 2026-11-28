#!/usr/bin/env python3
"""每日自检：点播站点可用性 + 直播线路可用性，保守调整后由 workflow 提交。

设计原则：宁可少动也不误删。
- 站点连续 3 次自检失败才移出（且剩余站点数不少于 6 个），被移出的每天复检，连续 2 次恢复就加回。
- 直播：节目列表固定 51 个频道、每个频道只露 1 条线路；备选线路全部放在 live-pool.m3u 后台。
  某台的现用线路连续 2 天不通，就从池子里换一条当天测通的；换不动就保持原样，绝不删台。
- 当天可用线路不足两成时判定为网络异常，整轮不做任何替换。
"""
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "config.json")
TV = os.path.join(ROOT, "tv.json")
LIVE = os.path.join(ROOT, "live.m3u")
POOL = os.path.join(ROOT, "live-pool.m3u")
STATE = os.path.join(ROOT, "state.json")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
FAIL_LIMIT = 3        # 站点连续失败几次动配置
RECOVER_LIMIT = 2     # 站点连续成功几次加回
MIN_SITES = 6         # 站点下限保护
SWITCH_LIMIT = 2      # 直播现用线路连续失败几次换备用
MIN_LIVE_RATIO = 0.2  # 当天可用线路低于两成视为网络异常
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
DRY = "--dry-run" in sys.argv


def get(url, timeout=10, cap=1200000):
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout, context=CTX) as r:
            return r.read(cap), round((time.time() - t0) * 1000)
    except Exception:
        return b"", None


def check_site(site):
    api = site["api"]
    url = api + ("&" if "?" in api else "?") + urllib.parse.urlencode({"ac": "list"})
    body, ms = get(url, timeout=12, cap=8 * 1024 * 1024)
    if not body:
        return False, None, "连不上"
    txt = body.decode("utf-8", "ignore")
    if '"class"' not in txt and "<class>" not in txt:
        return False, ms, "返回异常"
    return True, ms, txt


def load_lives(path):
    """返回 {频道名: {"tid","group","urls":[...]}}"""
    if not os.path.exists(path):
        return {}
    lines = [l.rstrip("\n") for l in open(path, encoding="utf-8") if l.strip() and not l.startswith("#EXTM3U")]
    groups = {}
    for i in range(0, len(lines) - 1, 2):
        ext, url = lines[i], lines[i + 1]
        if not ext.startswith("#EXTINF"):
            continue
        tname = (re.search(r'tvg-name="([^"]*)"', ext) or [None, ""])[1]
        tid = (re.search(r'tvg-id="([^"]*)"', ext) or [None, ""])[1]
        grp = (re.search(r'group-title="([^"]*)"', ext) or [None, ""])[1]
        g = groups.setdefault(tname, {"tid": tid, "group": grp, "urls": []})
        g["urls"].append(url)
    return groups


def check_line(url):
    """m3u8 能解析 + 首分片可取，才算这条线路可用。"""
    body, ms = get(url, timeout=8, cap=200000)
    if not body:
        return False, None
    txt = body.decode("utf-8", "ignore")
    base = url
    res = ""
    m = re.search(r"RESOLUTION=(\d+x\d+)", txt)
    if m:
        res = m.group(1)
    if "#EXT-X-STREAM-INF" in txt:
        nxt = [l.strip() for l in txt.splitlines() if l.strip() and not l.startswith("#")]
        if not nxt:
            return False, None
        vurl = urllib.parse.urljoin(base, nxt[0])
        d2, ms2 = get(vurl, timeout=8, cap=200000)
        if not d2:
            return False, None
        txt, base = d2.decode("utf-8", "ignore"), vurl
    segs = [l.strip() for l in txt.splitlines() if l.strip() and not l.startswith("#")]
    if not segs:
        return False, None
    seg_url = urllib.parse.urljoin(base, segs[0])
    d3, seg_ms = get(seg_url, timeout=8, cap=200000)
    if not d3:
        return False, None
    durs = [float(x) for x in re.findall(r"#EXTINF:\s*([0-9.]+)", txt)]
    dur = max(durs) if durs else 0
    cost = (ms or 0) + (seg_ms or 0) + max(0, dur - 6) * 400
    return True, {"cost": cost, "m3u8_ms": ms, "seg_ms": seg_ms, "dur": round(dur, 1), "res": res}


def write_live(groups, path):
    out = ["#EXTM3U"]
    for tname, g in groups.items():
        out.append('#EXTINF:-1 tvg-id="%s" tvg-name="%s" group-title="%s",%s' % (
            g["tid"], tname, g["group"], tname))
        out.append(g["urls"][0])
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cfg = json.load(open(CFG, encoding="utf-8"))
    try:
        state = json.load(open(STATE, encoding="utf-8"))
    except Exception:
        state = {}
    sites_state = state.get("sites", {})
    parked = state.get("parked", {})
    lines_state = state.get("lines", {})
    report = {"date": today, "sites": {}, "lines_swapped": [], "removed": [], "restored": []}

    # ---------- 点播站点 ----------
    print("== 点播站点自检 ==")
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(check_site, cfg["sites"]))
    alive = []
    for s, (ok, ms, extra) in zip(cfg["sites"], results):
        k = s["key"]
        st = sites_state.setdefault(k, {"fail_streak": 0, "ok_streak": 0, "last_ok": ""})
        if ok:
            st["fail_streak"] = 0
            st["ok_streak"] = st.get("ok_streak", 0) + 1
            st["last_ok"] = today
            report["sites"][k] = {"ok": True, "ms": ms}
        else:
            st["fail_streak"] = st.get("fail_streak", 0) + 1
            st["ok_streak"] = 0
            report["sites"][k] = {"ok": False, "ms": ms, "reason": extra, "streak": st["fail_streak"]}
            print("  × %-10s %s (连续失败 %d)" % (s["name"], extra, st["fail_streak"]))
        alive.append(s)

    ok_now = sum(1 for v in report["sites"].values() if v["ok"])
    net_ok = ok_now >= max(1, len(cfg["sites"]) * 0.5)
    report["net_ok"] = net_ok
    if not net_ok:
        print("  ! 本次可用站点仅 %d/%d，判定为网络异常，不做任何移出/替换" % (ok_now, len(cfg["sites"])))

    keep = []
    for s in alive:
        st = sites_state[s["key"]]
        if net_ok and st["fail_streak"] >= FAIL_LIMIT and len(alive) - len(report["removed"]) > MIN_SITES:
            parked[s["key"]] = s
            report["removed"].append(s["key"])
            print("  → 移出 %s（连续 %d 次失败）" % (s["name"], st["fail_streak"]))
            continue
        keep.append(s)

    if parked:
        print("== 复检已移出站点 ==")
        keys = list(parked)
        with ThreadPoolExecutor(max_workers=4) as ex:
            rs = list(ex.map(check_site, [parked[k] for k in keys]))
        for k, (ok, ms, extra) in zip(keys, rs):
            pst = parked[k]
            pst["ok_streak"] = pst.get("ok_streak", 0) + 1 if ok else 0
            print("  %s %-10s %s" % ("✓" if ok else "×", pst["name"], (ms or "-")))
            if ok and pst["ok_streak"] >= RECOVER_LIMIT:
                keep.append({"key": pst["key"], "name": pst["name"], "type": pst["type"],
                             "api": pst["api"], "searchable": pst.get("searchable", 1),
                             "quickSearch": pst.get("quickSearch", 1),
                             "filterable": pst.get("filterable", 1),
                             **({"categories": pst["categories"]} if pst.get("categories") else {})})
                del parked[k]
                report["restored"].append(k)
                print("  → 恢复 %s" % pst["name"])

    changed = len(keep) != len(cfg["sites"]) or report["restored"]
    if changed:
        order = {s["key"]: i for i, s in enumerate(cfg["sites"])}
        keep.sort(key=lambda s: order.get(s["key"], 999))
        cfg["sites"] = keep

    # ---------- 直播线路 ----------
    print("== 直播线路自检 ==")
    live_groups = load_lives(LIVE)
    pool_groups = load_lives(POOL)
    jobs = []
    for t, g in live_groups.items():
        jobs.append((t, "live", g["urls"][0]))
    for t, g in pool_groups.items():
        cur = (live_groups.get(t, {}).get("urls") or [None])[0]
        for u in g["urls"]:
            if u != cur:
                jobs.append((t, "pool", u))
    with ThreadPoolExecutor(max_workers=10) as ex:
        rs = list(ex.map(lambda j: check_line(j[2]), jobs))
    line_res = {}
    for (t, kind, u), (ok, info) in zip(jobs, rs):
        line_res[(t, kind, u)] = (ok, info)
        st = lines_state.setdefault(u, {"fail_streak": 0, "last_ok": "", "cost": None})
        if ok:
            st["fail_streak"] = 0
            st["last_ok"] = today
            st["cost"] = info["cost"]
        else:
            st["fail_streak"] = st.get("fail_streak", 0) + 1
        if not ok and kind == "live":
            print("  × %s 现用线路不通（连续 %d）" % (t, st["fail_streak"]))

    live_ok = sum(1 for (t, kind, u), (ok, _) in line_res.items() if kind == "live" and ok)
    live_total = len(live_groups)
    live_net_ok = bool(net_ok and live_total and live_ok >= live_total * MIN_LIVE_RATIO)
    report["live"] = {"ok": live_ok, "total": live_total, "net_ok": live_net_ok}
    print("  现用线路可用 %d/%d" % (live_ok, live_total))

    swapped = 0
    for t, g in live_groups.items():
        cur = g["urls"][0]
        f = lines_state.get(cur, {}).get("fail_streak", 0)
        if not live_net_ok or f < SWITCH_LIMIT:
            continue
        opts = [(line_res[(t, "pool", u)][1]["cost"], u)
                for u in (pool_groups.get(t, {}).get("urls") or [])
                if line_res.get((t, "pool", u), (False, None))[0]]
        if not opts:
            continue
        opts.sort()
        new = opts[0][1]
        g["urls"][0] = new
        lines_state.setdefault(new, {"fail_streak": 0, "last_ok": today, "cost": opts[0][0]})
        lines_state[cur]["fail_streak"] = 0
        swapped += 1
        report["lines_swapped"].append({"channel": t, "to": new})
        print("  ↔ %-13s 换成备用线路" % t)

    # ---------- 写回 ----------
    if not DRY:
        if changed:
            json.dump(cfg, open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            json.dump(cfg, open(TV, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print("已更新 config.json / tv.json（%d 站）" % len(cfg["sites"]))
        if swapped:
            write_live(live_groups, LIVE)
            print("已更新 live.m3u（%d 频道）" % len(live_groups))
        state = {"updated": today, "sites": sites_state, "parked": parked,
                 "lines": lines_state, "last_report": report}
        json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    okn = sum(1 for k, v in report["sites"].items() if v["ok"])
    print("\n汇总：站点 %d/%d 可用，移出 %d，恢复 %d；直播 %d/%d 可用，换线 %d" % (
        okn, len(cfg["sites"]), len(report["removed"]), len(report["restored"]),
        live_ok, live_total, swapped))
    with open(os.path.join(ROOT, "last-check.md"), "w", encoding="utf-8") as f:
        f.write("# 每日自检 %s\n\n- 点播：%d/%d 可用（移出 %d，恢复 %d）\n- 直播：%d/%d 个频道现用线路可用（换线 %d）\n\n" % (
            today, okn, len(cfg["sites"]), len(report["removed"]), len(report["restored"]),
            live_ok, live_total, swapped))
        for k, v in report["sites"].items():
            f.write("- 站点 %s：%s %s\n" % (k, "正常" if v["ok"] else "失败(" + str(v.get("reason")) + ")",
                                       (str(v["ms"]) + " ms") if v.get("ms") else ""))
        bad = [t for (t, kind, u), (ok, _) in line_res.items() if kind == "live" and not ok]
        if bad:
            f.write("- 当天不通的频道：%s\n" % "、".join(sorted(bad)))
    if DRY:
        print("(dry-run，未写入文件)")


if __name__ == "__main__":
    main()
