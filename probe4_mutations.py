#!/usr/bin/env python3
"""Probe 4 - GraphQL MUTATIONS under a downscoped GITHUB_TOKEN.

REST writes were measured tightly gated (403 issue-create under contents-read).
GraphQL mutations resolve through different authorization code, and the disclosed
corpus has two paid reports of exactly this shape (#2209433 read-only Issues token
modifying issue comments, #3527788 labels added to arbitrary issues/PRs).

Each mutation records whether it SUCCEEDED under a token that did not declare the
permission GitHub documents for the equivalent REST write.
"""
import json, os, urllib.request, urllib.error

TOK   = os.environ["PROBE_TOKEN"]
LABEL = os.environ["PROBE_LABEL"]

REPO_A   = "R_kgDOUN7EUA"
REPO_B   = "R_kgDOUN6qmQ"      # other PRIVATE repo - token must never write here
REPO_PUB = "R_kgDOUN6qbQ"
ISSUE_A  = "I_kwDOUN7EUM8AAAABPpWenw"
ISSUE_B  = "I_kwDOUN6qmc8AAAABPpSo8A"   # issue in the OTHER private repo
LABEL_A  = "LA_kwDOUN7EUM8AAAACztC33w"
REF_A    = "REF_kwDOUN7EUK9yZWZzL2hlYWRzL21haW4"
OID_A    = "9be424acedd3b11b977156deb8039ddfea298773"
REL_A    = "RE_kwDOUN7EUM4WzMS1"
ENV_A    = "EN_kwDOUN7EUM8AAAAE8Pnv8g"
USER     = "U_kgDODK_6uw"

rows = []

def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    h = {"Authorization": "Bearer " + TOK, "Content-Type": "application/json",
         "User-Agent": "mut-probe", "Accept": "application/vnd.github+json"}
    r = urllib.request.Request("https://api.github.com/graphql", data=body, headers=h, method="POST")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, str(e)

def mut(name, needs, query, variables=None):
    st, txt = gql(query, variables)
    ok, errs = False, []
    try:
        j = json.loads(txt)
        errs = [(e.get("type") or "") + "|" + e.get("message", "")[:110] for e in j.get("errors", [])]
        d = j.get("data") or {}
        # a mutation SUCCEEDED only if its payload is non-null
        ok = any(v is not None for v in d.values()) and not any(
            t.startswith("FORBIDDEN") or t.startswith("NOT_FOUND") or t.startswith("INSUFFICIENT")
            for t in errs)
    except Exception:
        errs = ["<unparseable>"]
    verdict = "SUCCESS" if ok else (errs[0].split("|")[0] or "err" if errs else "null")
    rows.append({"label": LABEL, "mutation": name, "needs": needs, "http": st,
                 "verdict": verdict, "errors": errs, "snip": txt[:300]})
    print(json.dumps(rows[-1]))

S = "%s" % LABEL

# ---------- issues:write class ----------
mut("addComment", "issues:write",
    'mutation($s:ID!){addComment(input:{subjectId:$s,body:"probe-'+S+'"}){clientMutationId commentEdge{node{id url}}}}', {"s": ISSUE_A})
mut("updateIssue", "issues:write",
    'mutation($i:ID!){updateIssue(input:{id:$i,body:"updated-by-'+S+'"}){issue{id body}}}', {"i": ISSUE_A})
mut("addLabelsToLabelable", "issues:write",
    'mutation($l:ID!,$x:[ID!]!){addLabelsToLabelable(input:{labelableId:$l,labelIds:$x}){clientMutationId labelable{__typename}}}', {"l": ISSUE_A, "x": [LABEL_A]})
mut("removeLabelsFromLabelable", "issues:write",
    'mutation($l:ID!,$x:[ID!]!){removeLabelsFromLabelable(input:{labelableId:$l,labelIds:$x}){clientMutationId}}', {"l": ISSUE_A, "x": [LABEL_A]})
mut("addReaction", "issues:write",
    'mutation($s:ID!){addReaction(input:{subjectId:$s,content:THUMBS_UP}){clientMutationId reaction{id}}}', {"s": ISSUE_A})
mut("closeIssue", "issues:write",
    'mutation($i:ID!){closeIssue(input:{issueId:$i}){issue{state}}}', {"i": ISSUE_A})
mut("reopenIssue", "issues:write",
    'mutation($i:ID!){reopenIssue(input:{issueId:$i}){issue{state}}}', {"i": ISSUE_A})
mut("pinIssue", "issues:write",
    'mutation($i:ID!){pinIssue(input:{issueId:$i}){issue{id}}}', {"i": ISSUE_A})
mut("addAssigneesToAssignable", "issues:write",
    'mutation($a:ID!,$u:[ID!]!){addAssigneesToAssignable(input:{assignableId:$a,assigneeIds:$u}){clientMutationId}}', {"a": ISSUE_A, "u": [USER]})
mut("createIssue", "issues:write",
    'mutation($r:ID!){createIssue(input:{repositoryId:$r,title:"probe-'+S+'"}){issue{number}}}', {"r": REPO_A})
mut("createLabel", "issues:write",
    'mutation($r:ID!){createLabel(input:{repositoryId:$r,name:"probe-'+S+'",color:"00ff00"}){label{id}}}', {"r": REPO_A})
mut("updateSubscription", "none/user",
    'mutation($s:ID!){updateSubscription(input:{subscribableId:$s,state:SUBSCRIBED}){subscribable{id}}}', {"s": ISSUE_A})

# ---------- contents:write class ----------
mut("createRef", "contents:write",
    'mutation($r:ID!,$o:GitObjectID!){createRef(input:{repositoryId:$r,name:"refs/heads/probe-'+S+'",oid:$o}){ref{name}}}', {"r": REPO_A, "o": OID_A})
mut("createCommitOnBranch", "contents:write",
    'mutation($o:GitObjectID!){createCommitOnBranch(input:{branch:{repositoryNameWithOwner:"antonade/gh-probe-a",branchName:"main"},expectedHeadOid:$o,message:{headline:"probe-'+S+'"},fileChanges:{additions:[{path:"probe-'+S+'.txt",contents:"cHJvYmU="}]}}){commit{oid}}}', {"o": OID_A})
mut("updateRef", "contents:write",
    'mutation($r:ID!,$o:GitObjectID!){updateRef(input:{refId:$r,oid:$o,force:false}){ref{name}}}', {"r": REF_A, "o": OID_A})

# ---------- administration class ----------
mut("updateRepository-desc", "administration:write",
    'mutation($r:ID!){updateRepository(input:{repositoryId:$r,description:"changed-by-'+S+'"}){repository{description}}}', {"r": REPO_A})
mut("updateRepositoryEnabledSettings", "administration:write",
    'mutation($r:ID!){updateRepository(input:{repositoryId:$r,hasIssuesEnabled:true}){repository{hasIssuesEnabled}}}', {"r": REPO_A})
mut("createEnvironment", "administration:write",
    'mutation($r:ID!){createEnvironment(input:{repositoryId:$r,name:"probe-env-'+S+'"}){environment{id name}}}', {"r": REPO_A})
mut("deleteEnvironment", "administration:write",
    'mutation($e:ID!){deleteEnvironment(input:{id:$e}){clientMutationId}}', {"e": ENV_A})
mut("createBranchProtectionRule", "administration:write",
    'mutation($r:ID!){createBranchProtectionRule(input:{repositoryId:$r,pattern:"probe-'+S+'"}){branchProtectionRule{id pattern}}}', {"r": REPO_A})
mut("enablePullRequestAutoMerge", "pull-requests:write",
    'mutation{enablePullRequestAutoMerge(input:{pullRequestId:"PR_kwDOAAAAAA"}){clientMutationId}}')

# ---------- star / user-level ----------
mut("addStar", "none (user)",
    'mutation($s:ID!){addStar(input:{starrableId:$s}){starrable{id}}}', {"s": REPO_PUB})

# ---------- CROSS-REPO writes: token must never reach repo B ----------
mut("XREPO-createIssue-B", "cross-repo",
    'mutation($r:ID!){createIssue(input:{repositoryId:$r,title:"xrepo-'+S+'"}){issue{number url}}}', {"r": REPO_B})
mut("XREPO-addComment-B", "cross-repo",
    'mutation($s:ID!){addComment(input:{subjectId:$s,body:"xrepo-'+S+'"}){commentEdge{node{url}}}}', {"s": ISSUE_B})
mut("XREPO-updateIssue-B", "cross-repo",
    'mutation($i:ID!){updateIssue(input:{id:$i,body:"xrepo-'+S+'"}){issue{body}}}', {"i": ISSUE_B})
mut("XREPO-addReaction-B", "cross-repo",
    'mutation($s:ID!){addReaction(input:{subjectId:$s,content:EYES}){reaction{id}}}', {"s": ISSUE_B})
mut("XREPO-addLabels-B", "cross-repo",
    'mutation($l:ID!,$x:[ID!]!){addLabelsToLabelable(input:{labelableId:$l,labelIds:$x}){clientMutationId}}', {"l": ISSUE_B, "x": [LABEL_A]})
mut("XREPO-transferIssue-AtoB", "cross-repo",
    'mutation($i:ID!,$r:ID!){transferIssue(input:{issueId:$i,repositoryId:$r}){issue{url}}}', {"i": ISSUE_A, "r": REPO_B})
mut("XREPO-updateRepository-B", "cross-repo",
    'mutation($r:ID!){updateRepository(input:{repositoryId:$r,description:"xrepo-'+S+'"}){repository{description}}}', {"r": REPO_B})
mut("XREPO-createRef-B", "cross-repo",
    'mutation($r:ID!,$o:GitObjectID!){createRef(input:{repositoryId:$r,name:"refs/heads/xrepo-'+S+'",oid:$o}){ref{name}}}', {"r": REPO_B, "o": OID_A})
mut("XREPO-addStar-B", "cross-repo",
    'mutation($s:ID!){addStar(input:{starrableId:$s}){starrable{id}}}', {"s": REPO_B})
mut("XREPO-updateSubscription-B", "cross-repo",
    'mutation($s:ID!){updateSubscription(input:{subscribableId:$s,state:SUBSCRIBED}){subscribable{id}}}', {"s": REPO_B})

print("=== DONE " + LABEL + " ===")
