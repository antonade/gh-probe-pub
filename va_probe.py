import json,os,urllib.request,urllib.error
T=os.environ["PROBE_TOKEN"]; L=os.environ["PROBE_LABEL"]; A="https://api.github.com"; R="antonade/gh-probe-a"
def req(m,u,b=None):
    h={"Authorization":"Bearer "+T,"Accept":"application/vnd.github+json","User-Agent":"va","X-GitHub-Api-Version":"2022-11-28"}
    d=json.dumps(b).encode() if b is not None else None
    if d: h["Content-Type"]="application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(u,data=d,headers=h,method=m),timeout=30) as x:
            return x.status,x.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e: return e.code,e.read().decode("utf-8","replace")
    except Exception as e: return -1,str(e)
def emit(probe,st,body):
    ghsa=[]
    try:
        j=json.loads(body)
        if isinstance(j,list): ghsa=[a.get("security_advisory",{}).get("ghsa_id") for a in j][:3]
        else:
            n=(((j.get("data") or {}).get("repository") or {}).get("vulnerabilityAlerts") or {}).get("nodes")
            if n: ghsa=[x.get("securityVulnerability",{}).get("advisory",{}).get("ghsaId") for x in n][:3]
    except Exception: pass
    print(json.dumps({"label":L,"probe":probe,"status":st,"len":len(body),
                      "ghsa":[g for g in ghsa if g],"snip":body[:110]}))
st,b=req("GET","%s/repos/%s/dependabot/alerts?per_page=100"%(A,R)); emit("REST dependabot/alerts",st,b)
st,b=req("POST","%s/graphql"%A,{"query":'{repository(owner:"antonade",name:"gh-probe-a"){vulnerabilityAlerts(first:100){totalCount nodes{securityVulnerability{advisory{ghsaId}package{name}}}}}}'}); emit("GraphQL vulnerabilityAlerts",st,b)
st,b=req("GET","%s/repos/%s/vulnerability-alerts"%(A,R)); emit("REST vulnerability-alerts (bool)",st,b)
st,b=req("POST","%s/graphql"%A,{"query":'{repository(owner:"antonade",name:"gh-probe-a"){hasVulnerabilityAlertsEnabled}}'}); emit("GraphQL hasVulnAlertsEnabled",st,b)
