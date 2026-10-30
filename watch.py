import json, re, os, requests
H = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1",
     "Accept-Language": "fr-FR,fr;q=0.9"}

def num(s):
    s = str(s).replace("\xa0", "").replace(" ", "")
    m = re.search(r"\d+(?:[.,]\d{1,2})?", s)
    return float(m.group().replace(",", ".")) if m else None

def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values(): yield from walk(v)
    elif isinstance(o, list):
        for v in o: yield from walk(v)

def price(html):
    ps = []
    for b in re.findall(r'<script[^>]+ld\+json[^>]*>(.*?)</script>', html, re.S):
        try: d = json.loads(b)
        except Exception: continue
        for o in walk(d):
            if "offers" in o:
                for f in walk(o["offers"]):
                    for k in ("price", "lowPrice"):
                        if k in f and num(f[k]) is not None: ps.append(num(f[k]))
    if ps: return min(ps)
    for pat in (r'property="(?:og|product):price:amount"\s+content="([^"]+)"',
                r'content="([^"]+)"\s+property="(?:og|product):price:amount"',
                r'itemprop="price"\s+content="([^"]+)"'):
        m = re.search(pat, html)
        if m and num(m.group(1)): return num(m.group(1))
    return None

items = json.load(open("items.json"))
topic = os.environ.get("NTFY_TOPIC")
for it in items:
    try:
        p = price(requests.get(it["url"], headers=H, timeout=25).text)
    except Exception:
        p = None
    it["last"] = p
    if p is None:
        it["error"] = True
        continue
    it["error"] = False
    if p <= float(it["max"]):
        if it.get("notified") != p and topic:
            msg = f'{it["name"]} : {p:g} € (ton max : {it["max"]} €). Taille souhaitée : {it.get("size") or "-"}'
            requests.post(f"https://ntfy.sh/{topic}", data=msg.encode(),
                          headers={"Title": "Promo !", "Click": it["url"], "Tags": "tada"})
            it["notified"] = p
    else:
        it["notified"] = None
json.dump(items, open("items.json", "w"), ensure_ascii=False, indent=1)
