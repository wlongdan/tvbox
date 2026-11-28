#!/usr/bin/env python3
"""每日自检：点播站点可用性 + 直播线路可用性，保守调整后由 workflow 提交。

设计原则：宁可少动也不误删。
- 站点连续 3 次自检失败才移出（且剩余站点数不少于 6 个）；
- 被移出的站点每天仍复检，连续 2 次恢复就加回；
- 线路只在「线路1 连续 3 次失败且线路2 正常」时互换，绝不删台；
- 全部正常时只更新 state.json，不动 config/live。
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
HD = os.path.join(ROOT, "live-hd.m3u")
STATE = os.path.join(ROOT, "state.json")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
FAIL_LIMIT = 3      # 连续失败几次动配置
RECOVER_LIMIT = 2   # 连续成功几次把站点加回
MIN_SITES = 6       # 站点下限保护
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
    """返回 [{tname, tid, group, urls:[...]}]"""
    if not os.path.exists(path):
        return []
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
    body, ms = get(url, timeout=10, cap=600000)
    if not body:
        return False, None
    txt = body.decode("utf-8", "ignore")
    return ("#EXTINF" in txt or "#EXT-X-STREAM-INF" in txt), ms


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
            alive.append(s)
            report["sites"][k] = {"ok": True, "ms": ms}
        else:
            st["fail_streak"] = st.get("fail_streak", 0) + 1
            st["ok_streak"] = 0
            alive.append(s)
            report["sites"][k] = {"ok": False, "ms": ms, "reason": extra, "streak": st["fail_streak"]}
            print("  × %-10s %s (连续失败 %d)" % (s["name"], extra, st["fail_streak"]))

    # 移出连续失败过多的站点
    keep = []
    for s in alive:
        st = sites_state[s["key"]]
        if st["fail_streak"] >= FAIL_LIMIT and len(alive) - len(report["removed"]) > MIN_SITES:
            parked[s["key"]] = s
            report["removed"].append(s["key"])
            print("  → 移出 %s（连续 %d 次失败）" % (s["name"], st["fail_streak"]))
            continue
        keep.append(s)

    # 复检已移出的站点
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
        # 按原顺序重排：保留原来的顺序优先
        order = {s["key"]: i for i, s in enumerate(cfg["sites"])}
        keep.sort(key=lambda s: order.get(s["key"], 999))
        cfg["sites"] = keep

    # ---------- 直播线路 ----------
    print("== 直播线路自检 ==")
    groups = load_lives(LIVE)
    jobs = []
    for tname, g in groups.items():
        for i, u in enumerate(g["urls"][:2]):
            jobs.append((tname, i, u))
    with ThreadPoolExecutor(max_workers=8) as ex:
        rs = list(ex.map(lambda j: check_line(j[2]), jobs))
    line_ok = {}
    for (tname, idx, u), (ok, ms) in zip(jobs, rs):
        line_ok[(tname, idx)] = ok
        st = lines_state.setdefault(u, {"fail_streak": 0, "last_ok": ""})
        if ok:
            st["fail_streak"] = 0
            st["last_ok"] = today
        else:
            st["fail_streak"] = st.get("fail_streak", 0) + 1

    swapped = 0
    for tname, g in groups.items():
        urls = g["urls"]
        if len(urls) < 2:
            continue
        u1, u2 = urls[0], urls[1]
        f1 = lines_state.get(u1, {}).get("fail_streak", 0)
        if f1 >= FAIL_LIMIT and lines_state.get(u2, {}).get("fail_streak", 0) == 0:
            g["urls"][0], g["urls"][1] = u2, u1
            lines_state[u1]["fail_streak"] = 0
            swapped += 1
            report["lines_swapped"].append({"channel": tname, "promoted": u2, "demoted": u1})
            print("  ↔ %-14s 线路2 提为线路1" % tname)
    total_lines = sum(len(g["urls"]) for g in groups.values())

    # ---------- 写回 ----------
    if not DRY:
        if changed:
            json.dump(cfg, open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            json.dump(cfg, open(TV, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print("已更新 config.json / tv.json（%d 站）" % len(cfg["sites"]))
        if swapped:
            out = ["#EXTM3U"]
            for tname, g in groups.items():
                for i, u in enumerate(g["urls"], 1):
                    out.append('#EXTINF:-1 tvg-id="%s" tvg-name="%s" group-title="%s",%s·线路%d' % (
                        g["tid"], tname, g["group"], tname, i))
                    out.append(u)
            open(LIVE, "w", encoding="utf-8").write("\n".join(out) + "\n")
            print("已更新 live.m3u（%d 条）" % sum(len(g["urls"]) for g in groups.values()))
        state = {"updated": today, "sites": sites_state, "parked": parked,
                 "lines": lines_state, "last_report": report}
        json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    okn = sum(1 for k, v in report["sites"].items() if v["ok"])
    print("\n汇总：站点 %d/%d 可用，移出 %d，恢复 %d；线路 %d 条，交换 %d" % (
        okn, len(cfg["sites"]), len(report["removed"]), len(report["restored"]), total_lines, swapped))
    with open(os.path.join(ROOT, "last-check.md"), "w", encoding="utf-8") as f:
        f.write("# 每日自检 %s\n\n- 站点：%d/%d 可用（移出 %d，恢复 %d）\n- 线路：%d 条（交换 %d）\n\n" % (
            today, okn, len(cfg["sites"]), len(report["removed"]), len(report["restored"]),
            total_lines, swapped))
        for k, v in report["sites"].items():
            f.write("- %s：%s %s\n" % (k, "正常" if v["ok"] else "失败(" + str(v.get("reason")) + ")",
                                    (str(v["ms"]) + " ms") if v.get("ms") else ""))
    if DRY:
        print("(dry-run，未写入文件)")


if __name__ == "__main__":
    main()
