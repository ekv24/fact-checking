import json, re, sys, os
src, mine, out = sys.argv[1], sys.argv[2], sys.argv[3]   # teammate dir, my news dir, output dir
rd=lambda p:[json.loads(l) for l in open(p,encoding='utf-8')]
corpus=rd(f"{src}/data/corpus.jsonl"); claims=rd(f"{src}/data/claims.jsonl")
news=rd(f"{mine}/data/news.jsonl"); prim=rd(f"{mine}/data/primary_sources.jsonl"); mclaims=rd(f"{mine}/data/claims.jsonl")
GROUP={"doc_001":"cbr_rate","doc_002":"cbr_rate","doc_003":"cpi","doc_004":"cpi","doc_005":"cpi",
       "doc_006":"nato","doc_007":"artemis","doc_008":"covid","doc_009":"olympics","doc_010":"nobel",
       "doc_011":"olympics26","doc_012":"who_stats"}
SPLIT={"cbr_rate":"test","cpi":"dev","nato":"dev","artemis":"dev","covid":"test","olympics":"test","nobel":"dev","olympics26":"test","who_stats":"dev"}
MONTHS="января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря"
def feats(t):
    return dict(has_number=bool(re.search(r"\d",t)), has_date=bool(re.search(MONTHS+r"|\b(19|20)\d\d\b",t)),
                has_exact_marker=bool(re.search(r"\bровно\b|\bтолько\b|\bвсе\b|\bни одн",t)))
# new corpus docs from my primary sources (own paraphrases)
for i,p in enumerate(prim):
    corpus.append(dict(doc_id=f"doc_{11+i:03d}",title=p["publisher"],publisher=p["publisher"],published_at=None,url=p["url"],
        sentences=[dict(sentence_id=k,text=s) for k,s in enumerate(p["sentences"])]))
pmap={"p01":"doc_011","p02":"doc_012"}
out_claims=[]
for c in claims:
    g=GROUP[c["anchor_doc_id"]]
    c.update(kind="fact",news_id=None,event_group=g,split=SPLIT[g],annotator="A0",verified_by_second=False,
             origin_detail="perturbed" if c["label"]=="REFUTES" else ("unsupported_detail" if c["label"]=="NOT_ENOUGH_INFO" else "extracted"),
             **feats(c["claim"]))
    out_claims.append(c)
n=len(out_claims)
for m in mclaims:
    n+=1; a=pmap[m["evidence"][0]["doc_id"]] if m["evidence"] else ("doc_011" if m["news_id"] in("n01","n02","n03") else "doc_012")
    g=GROUP[a]
    out_claims.append(dict(id=f"claim_{n:03d}",claim=m["claim"],kind=m["kind"],label=m["label"],
        evidence=[dict(doc_id=pmap[e["doc_id"]],sentence_id=e["sentence_id"]) for e in m["evidence"]],
        anchor_doc_id=a,news_id=m["news_id"],language="ru",as_of="2026-11-17",origin="news_derived",
        origin_detail=m["origin"],event_group=g,split=SPLIT[g],annotator="A1",verified_by_second=False,**feats(m["claim"])))
# opinion / unverifiable (evaluative or forecast: no evidence by design)
extra=[("Решение Банка России сохранить ставку было правильным.","opinion","doc_001"),
       ("Миссия Artemis I была самым важным событием в освоении космоса за последние годы.","opinion","doc_007"),
       ("Хан Ган заслужила Нобелевскую премию по литературе 2024 года больше всех остальных кандидатов.","opinion","doc_010"),
       ("Олимпийские игры в Париже 2024 года были лучшими в истории.","opinion","doc_009"),
       ("Инфляция в России к концу 2027 года обязательно снизится до 4%.","unverifiable","doc_001"),
       ("Следующая пандемия начнётся в течение десяти лет.","unverifiable","doc_008")]
for t,k,a in extra:
    n+=1; g=GROUP[a]
    out_claims.append(dict(id=f"claim_{n:03d}",claim=t,kind=k,label="NOT_ENOUGH_INFO",evidence=[],anchor_doc_id=a,news_id=None,
        language="ru",as_of="2026-11-17",origin="manually_written_opinion",origin_detail="evaluative_or_forecast",
        event_group=g,split=SPLIT[g],annotator="A1",verified_by_second=False,**feats(t)))
os.makedirs(f"{out}/data",exist_ok=True)
def dump(name,rows):
    with open(f"{out}/data/{name}","w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
dump("corpus.jsonl",corpus); dump("claims.jsonl",out_claims); dump("news.jsonl",news)
