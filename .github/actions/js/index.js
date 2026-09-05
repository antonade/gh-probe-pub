const t = process.env.ACTIONS_RUNTIME_TOKEN || "";
const u = process.env.ACTIONS_RESULTS_URL || "";
console.log("JS_RUNTIME_TOKEN_SET=" + (t ? "yes" : "no") + " len=" + t.length);
console.log("JS_RESULTS_URL_SET=" + (u ? "yes" : "no"));
if (t) {
  try {
    const p = JSON.parse(Buffer.from(t.split(".")[1], "base64").toString());
    console.log("JS_CLAIM_scp=" + JSON.stringify(p.scp || p.Permission || null).slice(0,300));
    console.log("JS_CLAIM_keys=" + JSON.stringify(Object.keys(p)));
  } catch (e) { console.log("JS_DECODE_ERR=" + e.message); }
}
