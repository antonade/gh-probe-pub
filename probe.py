#!/usr/bin/env python3
"""Scope-boundary probe. Runs inside GitHub Actions with a GITHUB_TOKEN whose
permissions were declared in the workflow. Records what that token can actually reach."""
import json, os, sys, urllib.request, urllib.error, hashlib

TOK   = os.environ["PROBE_TOKEN"]
LABEL = os.environ["PROBE_LABEL"]
OWNER = "antonade"
A     = "gh-probe-pub"     # this repo  (public)
B     = "gh-probe-priv"    # other repo (PRIVATE) - token must never reach it
CAN   = "CANARY_PRIVB_7f3a91c2"
NODE_REPO_B  = "R_kgDOUN6qmQ"
NODE_ISSUE_B = "I_kwDOUN6qmc8AAAABPpSo8A"
NODE_REPO_A  = "R_kgDOUN6qbQ"

rows = []

def req(method, url, body=None, hdrs=None):
    h = {"Authorization": "Bearer " + TOK,
         "Accept": "application/vnd.github+json",
         "X-GitHub-Api-Version": "2022-11-28",
         "User-Agent": "scope-probe"}
    if hdrs: h.update(hdrs)
    data = json.dumps(body).encode() if body is not None else None
    if data: h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, str(e)

def rec(family, name, method, url, body=None):
    st, txt = req(method, url, body)
    rows.append({"label": LABEL, "family": family, "probe": name, "method": method,
                 "url": url.replace("https://api.github.com", ""),
                 "status": st, "len": len(txt), "canary": CAN in txt,
                 "sha": hashlib.sha256(txt.encode()).hexdigest()[:12],
                 "snip": txt[:220]})

def gql(name, query, variables=None):
    st, txt = req("POST", "https://api.github.com/graphql",
                  {"query": query, "variables": variables or {}})
    try:
        j = json.loads(txt)
        errs = [ (e.get("type") or "") + "|" + (e.get("message","")[:90]) for e in j.get("errors",[]) ]
        d = j.get("data") or {}
        has_data = any(v is not None for v in d.values())
    except Exception:
        errs, has_data = ["<unparseable>"], False
    rows.append({"label": LABEL, "family": "graphql", "probe": name, "method": "POST",
                 "url": "/graphql", "status": st, "len": len(txt), "canary": CAN in txt,
                 "sha": hashlib.sha256(txt.encode()).hexdigest()[:12],
                 "gql_errors": errs, "gql_has_data": has_data, "snip": txt[:400]})

api = "https://api.github.com"

# ---------- meta ----------
rec("meta", "installation-repos", "GET", api + "/installation/repositories")
rec("meta", "rate_limit",         "GET", api + "/rate_limit")

# ---------- REST on OWN repo A: does the declared permission bind? ----------
own = [
 ("repo-meta",        "/repos/%s/%s" % (OWNER, A)),
 ("contents",         "/repos/%s/%s/contents/README.md" % (OWNER, A)),
 ("issues-list",      "/repos/%s/%s/issues" % (OWNER, A)),
 ("pulls",            "/repos/%s/%s/pulls" % (OWNER, A)),
 ("actions-secrets",  "/repos/%s/%s/actions/secrets" % (OWNER, A)),
 ("actions-vars",     "/repos/%s/%s/actions/variables" % (OWNER, A)),
 ("actions-runs",     "/repos/%s/%s/actions/runs" % (OWNER, A)),
 ("actions-artifacts","/repos/%s/%s/actions/artifacts" % (OWNER, A)),
 ("actions-perms",    "/repos/%s/%s/actions/permissions" % (OWNER, A)),
 ("collaborators",    "/repos/%s/%s/collaborators" % (OWNER, A)),
 ("hooks",            "/repos/%s/%s/hooks" % (OWNER, A)),
 ("deploy-keys",      "/repos/%s/%s/keys" % (OWNER, A)),
 ("environments",     "/repos/%s/%s/environments" % (OWNER, A)),
 ("deployments",      "/repos/%s/%s/deployments" % (OWNER, A)),
 ("releases",         "/repos/%s/%s/releases" % (OWNER, A)),
 ("labels",           "/repos/%s/%s/labels" % (OWNER, A)),
 ("milestones",       "/repos/%s/%s/milestones" % (OWNER, A)),
 ("commits",          "/repos/%s/%s/commits" % (OWNER, A)),
 ("git-refs",         "/repos/%s/%s/git/refs" % (OWNER, A)),
 ("branches",         "/repos/%s/%s/branches" % (OWNER, A)),
 ("code-scanning",    "/repos/%s/%s/code-scanning/alerts" % (OWNER, A)),
 ("dependabot-alerts","/repos/%s/%s/dependabot/alerts" % (OWNER, A)),
 ("secret-scanning",  "/repos/%s/%s/secret-scanning/alerts" % (OWNER, A)),
 ("traffic-views",    "/repos/%s/%s/traffic/views" % (OWNER, A)),
 ("pages",            "/repos/%s/%s/pages" % (OWNER, A)),
 ("invitations",      "/repos/%s/%s/invitations" % (OWNER, A)),
 ("rulesets",         "/repos/%s/%s/rulesets" % (OWNER, A)),
]
for n, p in own:
    rec("own-repo", n, "GET", api + p)

# writes on own repo (should require :write)
rec("own-repo-write", "issue-create", "POST", api + "/repos/%s/%s/issues" % (OWNER, A),
    {"title": "probe-write-" + LABEL, "body": "probe"})
rec("own-repo-write", "label-create", "POST", api + "/repos/%s/%s/labels" % (OWNER, A),
    {"name": "probe-" + LABEL, "color": "00ff00"})

# ---------- REST on PRIVATE repo B: cross-repository reach ----------
other = [
 ("repo-meta",      "/repos/%s/%s" % (OWNER, B)),
 ("contents",       "/repos/%s/%s/contents/SECRETFILE.txt" % (OWNER, B)),
 ("issues-list",    "/repos/%s/%s/issues" % (OWNER, B)),
 ("issue-1",        "/repos/%s/%s/issues/1" % (OWNER, B)),
 ("labels",         "/repos/%s/%s/labels" % (OWNER, B)),
 ("commits",        "/repos/%s/%s/commits" % (OWNER, B)),
 ("git-refs",       "/repos/%s/%s/git/refs" % (OWNER, B)),
 ("actions-secrets","/repos/%s/%s/actions/secrets" % (OWNER, B)),
 ("by-id",          "/repositories/1356769945"),
 ("by-id-contents", "/repositories/1356769945/contents/SECRETFILE.txt"),
 ("by-id-issues",   "/repositories/1356769945/issues"),
]
for n, p in other:
    rec("other-repo", n, "GET", api + p)
rec("other-repo-write", "issue-create", "POST", api + "/repos/%s/%s/issues" % (OWNER, B),
    {"title": "xrepo-write-" + LABEL, "body": "probe"})

# ---------- GraphQL: same boundaries, different code path ----------
gql("viewer", "query{viewer{login}}")
gql("rateLimit", "query{rateLimit{limit remaining nodeCount}}")
gql("repoA-basic", 'query{repository(owner:"%s",name:"%s"){name description isPrivate}}' % (OWNER, A))
gql("repoA-issues", 'query{repository(owner:"%s",name:"%s"){issues(first:5){nodes{title body}}}}' % (OWNER, A))
gql("repoA-blob", 'query{repository(owner:"%s",name:"%s"){object(expression:"HEAD:README.md"){... on Blob{text}}}}' % (OWNER, A))
gql("repoA-prs", 'query{repository(owner:"%s",name:"%s"){pullRequests(first:5){nodes{title}}}}' % (OWNER, A))
gql("repoA-discussions", 'query{repository(owner:"%s",name:"%s"){discussions(first:5){nodes{title}}}}' % (OWNER, A))
gql("repoA-releases", 'query{repository(owner:"%s",name:"%s"){releases(first:5){nodes{name}}}}' % (OWNER, A))
gql("repoA-deploykeys", 'query{repository(owner:"%s",name:"%s"){deployKeys(first:5){nodes{title}}}}' % (OWNER, A))
gql("repoA-collabs", 'query{repository(owner:"%s",name:"%s"){collaborators(first:5){nodes{login}}}}' % (OWNER, A))
gql("repoA-vulnalerts", 'query{repository(owner:"%s",name:"%s"){vulnerabilityAlerts(first:5){nodes{id}}}}' % (OWNER, A))

# cross-repo via GraphQL
gql("repoB-byname", 'query{repository(owner:"%s",name:"%s"){name description isPrivate}}' % (OWNER, B))
gql("repoB-byname-blob", 'query{repository(owner:"%s",name:"%s"){object(expression:"HEAD:SECRETFILE.txt"){... on Blob{text}}}}' % (OWNER, B))
gql("repoB-byname-issues", 'query{repository(owner:"%s",name:"%s"){issues(first:5){nodes{title body}}}}' % (OWNER, B))
gql("repoB-node", 'query($i:ID!){node(id:$i){... on Repository{name description isPrivate url}}}', {"i": NODE_REPO_B})
gql("repoB-node-blob", 'query($i:ID!){node(id:$i){... on Repository{object(expression:"HEAD:SECRETFILE.txt"){... on Blob{text}}}}}', {"i": NODE_REPO_B})
gql("repoB-node-issues", 'query($i:ID!){node(id:$i){... on Repository{issues(first:5){nodes{title body}}}}}', {"i": NODE_REPO_B})
gql("issueB-node", 'query($i:ID!){node(id:$i){... on Issue{title body url}}}', {"i": NODE_ISSUE_B})
gql("nodes-batch", 'query($a:[ID!]!){nodes(ids:$a){... on Repository{name isPrivate} ... on Issue{title body}}}',
    {"a": [NODE_REPO_B, NODE_ISSUE_B]})
gql("search-canary", 'query{search(query:"%s",type:ISSUE,first:5){nodes{... on Issue{title body repository{nameWithOwner}}}}}' % CAN)
gql("search-repo", 'query{search(query:"gh-probe-priv",type:REPOSITORY,first:5){nodes{... on Repository{nameWithOwner isPrivate}}}}')
gql("viewer-repos", 'query{viewer{repositories(first:20,privacy:PRIVATE){nodes{nameWithOwner isPrivate}}}}')
gql("repoB-mutation-issue",
    'mutation($r:ID!){createIssue(input:{repositoryId:$r,title:"xrepo-gql-probe"}){issue{number url}}}',
    {"r": NODE_REPO_B})

print("=== PROBE RESULTS " + LABEL + " ===")
for r in rows:
    print(json.dumps(r))
with open("probe-" + LABEL + ".jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
