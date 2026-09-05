import json,os,urllib.request,urllib.error
T=os.environ["PROBE_TOKEN"]; L=os.environ["PROBE_LABEL"]; A="https://api.github.com"; R="antonade/gh-probe-pub"
def g(u):
    h={"Authorization":"Bearer "+T,"Accept":"application/vnd.github+json","User-Agent":"ri"}
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers=h),timeout=25) as x: return x.status,x.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e: return e.code,e.read().decode("utf-8","replace")
for probe,u in (("rule-suites","%s/repos/%s/rulesets/rule-suites?per_page=10"%(A,R)),
                ("rule-suite-detail","%s/repos/%s/rulesets/rule-suites/3954854567"%(A,R)),
                ("rulesets","%s/repos/%s/rulesets"%(A,R))):
    st,b=g(u)
    n=None; actor=None
    try:
        j=json.loads(b)
        if isinstance(j,list): n=len(j); actor=(j[0].get("actor_name") if j else None)
        else: n="obj"; actor=j.get("actor_name")
    except Exception: pass
    print(json.dumps({"label":L,"probe":probe,"status":st,"n":n,"actor":actor,"snip":b[:90]}))
