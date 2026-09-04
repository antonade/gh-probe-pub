#!/usr/bin/env python3
"""Probe 5 - alias routes and cross-repo aggregators under a downscoped GITHUB_TOKEN.

Two hypotheses:
  (A) ALIAS ROUTES. /repos/{owner}/{repo}/X and /repositories/{id}/X reach the same resource.
      If their permission checks are wired separately, one may be reachable where the other is 403.
  (B) AGGREGATORS. /issues, /user/issues and /search return objects ACROSS repositories.
      A GITHUB_TOKEN is scoped to one repository. If an aggregator returns rows from a repo the
      token cannot address directly, that is a cross-repository escape -- the exact shape of the
      paying disclosed class.

This job runs in the PUBLIC repo gh-probe-pub. The PRIVATE repo gh-probe-a carries CANARY_A_1122.
Any appearance of that canary is a leak.
"""
import json, os, urllib.request, urllib.error, hashlib

TOK   = os.environ["PROBE_TOKEN"]
LABEL = os.environ["PROBE_LABEL"]
API   = "https://api.github.com"
OWNER = "antonade"
PUB, PUB_ID   = "gh-probe-pub", 1356769901     # this repo (token's scope)
PRIV, PRIV_ID = "gh-probe-a",   1356776528     # PRIVATE, token must not reach
CAN = "CANARY_A_1122"

rows = []

def req(url):
    h = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
         "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "alias-probe"}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, str(e)

def rec(group, name, url):
    st, txt = req(API + url)
    leak = CAN in txt
    rows.append({"label": LABEL, "group": group, "probe": name, "url": url,
                 "status": st, "len": len(txt), "canary": leak,
                 "sha": hashlib.sha256(txt.encode()).hexdigest()[:10],
                 "snip": txt[:200]})
    print(json.dumps(rows[-1]))

# ---------- (A) alias routes: named path vs numeric-id path, same resource ----------
PAIRS = [
    ("repo-meta",       "",                          ""),
    ("issues",          "/issues",                   "/issues"),
    ("issue-1",         "/issues/1",                 "/issues/1"),
    ("contents",        "/contents/README.md",       "/contents/README.md"),
    ("pulls",           "/pulls",                    "/pulls"),
    ("labels",          "/labels",                   "/labels"),
    ("releases",        "/releases",                 "/releases"),
    ("git-refs",        "/git/refs",                 "/git/refs"),
    ("commits",         "/commits",                  "/commits"),
    ("actions-secrets", "/actions/secrets",          "/actions/secrets"),
    ("hooks",           "/hooks",                    "/hooks"),
    ("keys",            "/keys",                     "/keys"),
    ("collaborators",   "/collaborators",            "/collaborators"),
]
for name, a, b in PAIRS:
    # the token's OWN repo, both route shapes
    rec("alias-own-named", name, "/repos/%s/%s%s" % (OWNER, PUB, a))
    rec("alias-own-byid",  name, "/repositories/%d%s" % (PUB_ID, b))
    # the PRIVATE repo, both route shapes
    rec("alias-priv-named", name, "/repos/%s/%s%s" % (OWNER, PRIV, a))
    rec("alias-priv-byid",  name, "/repositories/%d%s" % (PRIV_ID, b))

# ---------- (B) cross-repo aggregators ----------
AGG = [
    ("issues-global",        "/issues?filter=all&state=all&per_page=100"),
    ("user-issues",          "/user/issues?filter=all&state=all&per_page=100"),
    ("issues-orgs",          "/user/issues?filter=repos&state=all&per_page=100"),
    ("user-repos",           "/user/repos?per_page=100&visibility=all"),
    ("user-repos-private",   "/user/repos?per_page=100&visibility=private"),
    ("search-issues-canary", "/search/issues?q=" + CAN),
    ("search-issues-user",   "/search/issues?q=author:%s+type:issue" % OWNER),
    ("search-repos-user",    "/search/repositories?q=user:%s" % OWNER),
    ("search-code-canary",   "/search/code?q=" + CAN),
    ("user-starred",         "/user/starred?per_page=100"),
    ("user-subscriptions",   "/user/subscriptions?per_page=100"),
    ("notifications",        "/notifications?all=true&per_page=100"),
    ("user-orgs",            "/user/orgs"),
    ("user-packages-npm",    "/user/packages?package_type=npm"),
    ("users-owner-repos",    "/users/%s/repos?type=all&per_page=100" % OWNER),
    ("users-owner-events",   "/users/%s/events?per_page=100" % OWNER),
]
for name, u in AGG:
    rec("aggregator", name, u)

print("=== DONE " + LABEL + " ===")
