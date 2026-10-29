import base64
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "Mancat sources"
KEY = os.environ.get("MANCAT_SOURCES_KEY", os.path.expanduser("~/keys/mancat-sources.pem"))
SAFE = re.compile(r"^[A-Za-z0-9_\-]+\.json$")
BLOCKED = re.compile(r"yaoi|yuri|boys.?love|shounen.?ai|shoujo.?ai|lesbian|\bgay\b|lgbt", re.I)


def public_key():
    der = subprocess.run(["openssl", "ec", "-in", KEY, "-pubout", "-outform", "DER"],
                         check=True, capture_output=True).stdout
    return base64.b64encode(der).decode()


def main():
    files, sources, catalog = {}, [], []
    for f in sorted(os.listdir(ROOT)):
        if f in ("index.json", "catalog.json", "bundle.json") or not SAFE.match(f):
            continue
        body = open(os.path.join(ROOT, f), "rb").read()
        files[f] = hashlib.sha256(body).hexdigest()
        if f == "network.json":
            continue
        d = json.loads(body)
        for field in ("id", "name", "url", "theme", "lang"):
            if field not in d:
                sys.exit(f"{f}: missing {field}")
        if f != d["id"] + ".json":
            sys.exit(f"{f}: file name must be {d['id']}.json")
        if BLOCKED.search(d["id"] + " " + d["name"] + " " + d["url"]):
            sys.exit(f"{f}: blocked content")
        sources.append(f)
        catalog.append(d)
    bundle = {}
    for f in files:
        bundle[f] = open(os.path.join(ROOT, f), encoding="utf-8").read()
    bundle_raw = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    open(os.path.join(ROOT, "bundle.json"), "wb").write(bundle_raw)
    index = {"name": NAME, "key": public_key(), "files": files, "sources": sources,
             "bundle": {"file": "bundle.json", "sha256": hashlib.sha256(bundle_raw).hexdigest()}}
    if "network.json" in files:
        index["network"] = "network.json"
    raw = json.dumps(index, indent=1, sort_keys=True).encode()
    open(os.path.join(ROOT, "index.json"), "wb").write(raw)
    sig = subprocess.run(["openssl", "dgst", "-sha256", "-sign", KEY], input=raw, check=True, capture_output=True).stdout
    open(os.path.join(ROOT, "index.sig"), "w").write(base64.b64encode(sig).decode() + "\n")
    json.dump(catalog, open(os.path.join(ROOT, "catalog.json"), "w"), ensure_ascii=False, indent=1)
    print(f"{NAME}: {len(sources)} sources, {len(files)} files")


if __name__ == "__main__":
    main()
