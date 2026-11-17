import json,sys,collections,difflib
d=sys.argv[1]; rd=lambda n:[json.loads(l) for l in open(f"{d}/data/{n}",encoding="utf-8")]
co,cl,nw=rd("corpus.jsonl"),rd("claims.jsonl"),rd("news.jsonl")
sent={x["doc_id"]:len(x["sentences"]) for x in co}; nids={n["id"] for n in nw}
e=[]
if len({c["id"] for c in cl})!=len(cl): e.append("dup ids")
for c in cl:
    if c["label"] not in("SUPPORTS","REFUTES","NOT_ENOUGH_INFO"): e.append((c["id"],"label"))
    if c["kind"] not in("fact","opinion","unverifiable"): e.append((c["id"],"kind"))
    if c["kind"]!="fact" and c["label"]!="NOT_ENOUGH_INFO": e.append((c["id"],"non-fact must be NEI"))
    if c["label"]=="NOT_ENOUGH_INFO" and c["evidence"]: e.append((c["id"],"NEI evidence"))
    if c["label"]!="NOT_ENOUGH_INFO" and not c["evidence"]: e.append((c["id"],"no evidence"))
    if c["news_id"] and c["news_id"] not in nids: e.append((c["id"],"news_id"))
    for ev in c["evidence"]:
        if ev["doc_id"] not in sent or ev["sentence_id"]>=sent[ev["doc_id"]]: e.append((c["id"],"evidence ref"))
print("errors:",e)
print("n=",len(cl),dict(collections.Counter(c["label"] for c in cl)),dict(collections.Counter(c["kind"] for c in cl)))
print("split:",dict(collections.Counter(c["split"] for c in cl)))
# group leakage: no event_group in two splits
g=collections.defaultdict(set)
for c in cl:g[c["event_group"]].add(c["split"])
print("leaky groups:",[k for k,v in g.items() if len(v)>1])
# shortcut check: exact-marker words by label
m=collections.Counter((c["label"],c["has_exact_marker"]) for c in cl); print("exact-marker by label:",dict(m))
