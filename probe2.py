#!/usr/bin/env python3
"""Scope-boundary probe v2.

Runs inside GitHub Actions. Repo A is PRIVATE, so an anonymous request gets 404 for
everything -- any 200 here is attributable to the GITHUB_TOKEN and can be compared
against the permission the workflow actually declared.

Each row carries `needs`, the permission GitHub documents for that endpoint, so the
grid says directly whether a declared-permission boundary held.
"""
import json, os, urllib.request, urllib.error, hashlib

TOK   = os.environ["PROBE_TOKEN"]
LABEL = os.environ["PROBE_LABEL"]
OWNER = "antonade"
A     = "gh-probe-a"       # THIS repo, PRIVATE
B     = "gh-probe-priv"    # other repo, PRIVATE - token must never reach it
A_ID  = 1356776528
B_ID  = 1356769945
NODE_A       = "R_kgDOUN7EUA"
NODE_B       = "R_kgDOUN6qmQ"
NODE_ISSUE_B = "I_kwDOUN6qmc8AAAABPpSo8A"

CANARIES = {
    "content":  "CANARY_A_1122",
    "deploykey":"CANARY_DK_5b2e",
    "hookurl":  "CANARY_HOOK_9c1d",
    "hooksec":  "CANARY_HOOKSECRET_4a7e",
    "varval":   "CANARY_VARVAL_2f8b",
    "secretval":"CANARY_SECRETVAL_8d3f",
    "release":  "CANARY_REL_3344",
    "privb":    "CANARY_PRIVB_7f3a91c2",
}

rows = []

def req(method, url, body=None):
    h = {"Authorization": "Bearer " + TOK,
         "Accept": "application/vnd.github+json",
         "X-GitHub-Api-Version": "2022-11-28",
         "User-Agent": "scope-probe"}
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

def hits(txt):
    return [k for k, v in CANARIES.items() if v in txt]

def rec(family, name, needs, method, url, body=None):
    st, txt = req(method, url, body)
    rows.append({"label": LABEL, "family": family, "probe": name, "needs": needs,
                 "method": method, "url": url.replace("https://api.github.com", ""),
                 "status": st, "len": len(txt), "canary": hits(txt),
                 "sha": hashlib.sha256(txt.encode()).hexdigest()[:12],
                 "snip": txt[:260]})

def gql(name, needs, query, variables=None):
    st, txt = req("POST", "https://api.github.com/graphql",
                  {"query": query, "variables": variables or {}})
    errs, has_data, n = ["<unparseable>"], False, None
    try:
        j = json.loads(txt)
        errs = [(e.get("type") or "") + "|" + (e.get("message", "")[:100]) for e in j.get("errors", [])]
        d = j.get("data") or {}
        has_data = any(v is not None for v in d.values())
        n = txt.count('"')
    except Exception:
        pass
    rows.append({"label": LABEL, "family": "graphql", "probe": name, "needs": needs,
                 "method": "POST", "url": "/graphql", "status": st, "len": len(txt),
                 "canary": hits(txt), "sha": hashlib.sha256(txt.encode()).hexdigest()[:12],
                 "gql_errors": errs, "gql_has_data": has_data, "snip": txt[:520]})

api = "https://api.github.com"
RA = "/repos/%s/%s" % (OWNER, A)
RB = "/repos/%s/%s" % (OWNER, B)

# ---------- meta / cross-account ----------
rec("meta", "installation-repos", "none",     "GET", api + "/installation/repositories")
rec("meta", "user-repos",         "user",     "GET", api + "/user/repos?per_page=100&visibility=private")
rec("meta", "user",               "user",     "GET", api + "/user")
rec("meta", "user-installations", "user",     "GET", api + "/user/installations")
rec("meta", "users-antonade-repos","none",    "GET", api + "/users/antonade/repos?type=all")

# ---------- REST on OWN private repo A ----------
own = [
 ("repo-meta",          "metadata",       RA),
 ("contents",           "contents:read",  RA + "/contents/PRIVFILE.txt"),
 ("tarball",            "contents:read",  RA + "/tarball/main"),
 ("git-refs",           "contents:read",  RA + "/git/refs"),
 ("commits",            "contents:read",  RA + "/commits"),
 ("branches",           "contents:read",  RA + "/branches"),
 ("issues-list",        "issues:read",    RA + "/issues"),
 ("issue-1",            "issues:read",    RA + "/issues/1"),
 ("issue-events",       "issues:read",    RA + "/issues/events"),
 ("issue-timeline",     "issues:read",    RA + "/issues/1/timeline"),
 ("pulls",              "pull-requests:read", RA + "/pulls"),
 ("labels",             "issues|pr:read", RA + "/labels"),
 ("milestones",         "issues|pr:read", RA + "/milestones"),
 ("releases",           "contents:read",  RA + "/releases"),
 ("deployments",        "deployments:read", RA + "/deployments"),
 ("environments",       "?",              RA + "/environments"),
 ("env-canary",         "?",              RA + "/environments/canary-env"),
 ("actions-secrets",    "secrets:read (ADMIN)", RA + "/actions/secrets"),
 ("actions-secret-one", "secrets:read (ADMIN)", RA + "/actions/secrets/CANARY_SECRET"),
 ("actions-vars",       "variables:read (ADMIN)", RA + "/actions/variables"),
 ("actions-var-one",    "variables:read (ADMIN)", RA + "/actions/variables/CANARY_VAR"),
 ("dependabot-secrets", "dependabot_secrets (ADMIN)", RA + "/dependabot/secrets"),
 ("codespaces-secrets", "codespaces_secrets (ADMIN)", RA + "/codespaces/secrets"),
 ("actions-runs",       "actions:read",   RA + "/actions/runs"),
 ("actions-workflows",  "actions:read",   RA + "/actions/workflows"),
 ("actions-artifacts",  "actions:read",   RA + "/actions/artifacts"),
 ("actions-cache",      "actions:read",   RA + "/actions/cache/usage"),
 ("actions-runners",    "administration", RA + "/actions/runners"),
 ("actions-perms",      "administration", RA + "/actions/permissions"),
 ("actions-oidc-sub",   "administration", RA + "/actions/oidc/customization/sub"),
 ("hooks",              "administration (ADMIN)", RA + "/hooks"),
 ("hook-one",           "administration (ADMIN)", RA + "/hooks/674340897"),
 ("hook-config",        "administration (ADMIN)", RA + "/hooks/674340897/config"),
 ("deploy-keys",        "administration (ADMIN)", RA + "/keys"),
 ("deploy-key-one",     "administration (ADMIN)", RA + "/keys/162253453"),
 ("collaborators",      "push access",    RA + "/collaborators"),
 ("invitations",        "administration", RA + "/invitations"),
 ("teams",              "administration", RA + "/teams"),
 ("interaction-limits", "administration", RA + "/interaction-limits"),
 ("branch-protection",  "administration", RA + "/branches/main/protection"),
 ("rulesets",           "administration", RA + "/rulesets"),
 ("rules-branch",       "?",              RA + "/rules/branches/main"),
 ("vuln-alerts-status", "administration", RA + "/vulnerability-alerts"),
 ("dependabot-alerts",  "security_events", RA + "/dependabot/alerts"),
 ("code-scanning",      "security_events", RA + "/code-scanning/alerts"),
 ("secret-scanning",    "secret_scanning_alerts", RA + "/secret-scanning/alerts"),
 ("security-advisories","?",              RA + "/security-advisories"),
 ("sbom",               "contents:read",  RA + "/dependency-graph/sbom"),
 ("traffic-views",      "administration", RA + "/traffic/views"),
 ("traffic-clones",     "administration", RA + "/traffic/clones"),
 ("community-profile",  "metadata",       RA + "/community/profile"),
 ("topics",             "metadata",       RA + "/topics"),
 ("subscription",       "metadata",       RA + "/subscription"),
 ("pages",              "pages:read",     RA + "/pages"),
 ("codespaces",         "codespaces",     RA + "/codespaces"),
 ("packages",           "packages:read",  RA + "/packages?package_type=container"),
]
for n, need, p in own:
    rec("own", n, need, "GET", api + p)

# ---------- REST on the OTHER private repo B ----------
other = [
 ("repo-meta",     "metadata",      RB),
 ("contents",      "contents:read", RB + "/contents/SECRETFILE.txt"),
 ("issues",        "issues:read",   RB + "/issues"),
 ("by-id",         "metadata",      "/repositories/%d" % B_ID),
 ("by-id-contents","contents:read", "/repositories/%d/contents/SECRETFILE.txt" % B_ID),
]
for n, need, p in other:
    rec("other", n, need, "GET", api + p)

# ---------- GraphQL: same objects, different authz code path ----------
def rq(inner):
    return 'query{repository(owner:"%s",name:"%s"){%s}}' % (OWNER, A, inner)

gql("viewer",        "none", "query{viewer{login}}")
gql("A-basic",       "metadata", rq("name isPrivate visibility diskUsage"))
gql("A-blob",        "contents:read", rq('object(expression:"HEAD:PRIVFILE.txt"){... on Blob{text}}'))
gql("A-issues",      "issues:read", rq("issues(first:5){nodes{title body}}"))
gql("A-prs",         "pull-requests:read", rq("pullRequests(first:5){nodes{title}}"))
gql("A-releases",    "contents:read", rq("releases(first:5){nodes{name description}}"))
gql("A-deploykeys",  "administration (ADMIN)", rq("deployKeys(first:10){nodes{id title key readOnly}}"))
gql("A-collabs",     "push access", rq("collaborators(first:10){nodes{login}}"))
gql("A-vulnalerts",  "security_events", rq("vulnerabilityAlerts(first:20){nodes{id state securityVulnerability{package{name} advisory{summary ghsaId}} vulnerableManifestPath}}"))
gql("A-vulnenabled", "administration", rq("hasVulnerabilityAlertsEnabled"))
gql("A-branchprot",  "administration", rq("branchProtectionRules(first:5){nodes{id pattern}}"))
gql("A-rulesets",    "administration", rq("rulesets(first:5){nodes{name enforcement}}"))
gql("A-environments","?", rq("environments(first:10){nodes{name id}}"))
gql("A-interaction", "administration", rq("interactionAbility{limit expiresAt}"))
gql("A-deployments", "deployments:read", rq("deployments(first:5){nodes{id}}"))
gql("A-discussions", "discussions:read", rq("discussions(first:5){nodes{title body}}"))
gql("A-projectsv2",  "repository-projects", rq("projectsV2(first:5){nodes{title}}"))
gql("A-packages",    "packages:read", rq("packages(first:5){nodes{name}}"))
gql("A-forks",       "metadata", rq("forks(first:5){nodes{nameWithOwner}}"))
gql("A-assignable",  "metadata", rq("assignableUsers(first:10){nodes{login email}}"))
gql("A-mentionable", "metadata", rq("mentionableUsers(first:10){nodes{login email}}"))
gql("A-watchers",    "metadata", rq("watchers(first:10){nodes{login email}}"))
gql("A-labels",      "issues:read", rq("labels(first:20){nodes{name}}"))
gql("A-milestones",  "issues:read", rq("milestones(first:5){nodes{title}}"))
gql("A-refs",        "contents:read", rq('refs(refPrefix:"refs/heads/",first:10){nodes{name target{oid}}}'))
gql("A-history",     "contents:read", rq('defaultBranchRef{target{... on Commit{history(first:5){nodes{oid message}}}}}'))
gql("A-codeowners",  "contents:read", rq("codeowners{errors{kind}}"))
gql("A-securitypolicy","metadata", rq("isSecurityPolicyEnabled securityPolicyUrl"))
gql("A-node",        "metadata", 'query($i:ID!){node(id:$i){... on Repository{name isPrivate deployKeys(first:5){nodes{title key}}}}}', {"i": NODE_A})

# cross-repo through GraphQL
gql("B-byname", "cross-repo", 'query{repository(owner:"%s",name:"%s"){name isPrivate}}' % (OWNER, B))
gql("B-node",   "cross-repo", 'query($i:ID!){node(id:$i){... on Repository{name isPrivate object(expression:"HEAD:SECRETFILE.txt"){... on Blob{text}}}}}', {"i": NODE_B})
gql("B-issue-node", "cross-repo", 'query($i:ID!){node(id:$i){... on Issue{title body}}}', {"i": NODE_ISSUE_B})
gql("B-search", "cross-repo", 'query{search(query:"%s",type:ISSUE,first:5){nodes{... on Issue{title body repository{nameWithOwner}}}}}' % CANARIES["privb"])
gql("viewer-private-repos", "cross-repo", 'query{viewer{repositories(first:30,privacy:PRIVATE){nodes{nameWithOwner}}}}')

print("=== PROBE2 RESULTS " + LABEL + " ===")
for r in rows:
    print(json.dumps(r))
