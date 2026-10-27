"""Clasificador de venta entrenado con las etiquetas de septiembre (V/N de la auditoría anterior).
Se aplica igual a todos los meses para que «venta» signifique lo mismo mes a mes.
Uso: python3 -I venta_model.py <dir_qa>  -> out/venta_prob.json {id: prob}"""
import json, sys, re, collections
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_predict, StratifiedKFold
D = sys.argv[1]
src = open(D + '/qa_engine.py', encoding='utf-8').read()
g = {'__name__': 'eng'}; sys.argv = ['x', D]
exec(compile(src[:src.index('# ---------------------------------------------------------------- reglas')], 'eng', 'exec'), g)
LL, norm = g['LL'], g['norm']

def texto(c):
    ts = c['tx']; n = len(ts)
    parte = ts[int(n * 0.35):]
    return ' '.join(('qa ' if q == 0 else 'qc ') + norm(t) for _, q, t in parte)

grp = lambda op: 'U' if op == 'Upsell' else 'O'
probs, rep = {}, {}
for G in ['U', 'O']:
    cs = [c for c in LL if grp(c['op']) == G]
    X = [texto(c) for c in cs]
    tr = [i for i, c in enumerate(cs) if c['old'] in ('V', 'N')]
    y = np.array([1 if cs[i]['old'] == 'V' else 0 for i in tr])
    vec = TfidfVectorizer(ngram_range=(1, 3), min_df=4, max_df=0.6, sublinear_tf=True, max_features=200000)
    Xa = vec.fit_transform(X)
    clf = LogisticRegression(C=4, max_iter=3000, class_weight='balanced')
    p_cv = cross_val_predict(clf, Xa[tr], y, cv=StratifiedKFold(5, shuffle=True, random_state=1), method='predict_proba')[:, 1]
    # umbral que iguala la tasa de venta de septiembre
    thr = float(np.quantile(p_cv, 1 - y.mean()))
    pred = p_cv >= thr
    acc = (pred == y).mean(); prec = (pred & (y == 1)).sum() / max(1, pred.sum()); rec = (pred & (y == 1)).sum() / max(1, y.sum())
    rep[G] = dict(n=len(tr), base=float(y.mean()), thr=thr, acc=float(acc), prec=float(prec), rec=float(rec))
    clf.fit(Xa[tr], y)
    p_all = clf.predict_proba(Xa)[:, 1]
    for i, c in enumerate(cs):
        probs[c['id']] = round(float(p_cv[tr.index(i)] if i in set(tr) and False else p_all[i]), 4)
    # en septiembre (entrenamiento) se usa la predicción cruzada para no inflar el acuerdo
    for k, i in enumerate(tr): probs[cs[i]['id']] = round(float(p_cv[k]), 4)
    rep[G]['thr'] = thr
    # palabras con más peso (para revisar que tenga sentido)
    fn = np.array(vec.get_feature_names_out()); co = clf.coef_[0]
    rep[G]['top_v'] = list(fn[np.argsort(-co)[:25]]); rep[G]['top_n'] = list(fn[np.argsort(co)[:15]])
json.dump(dict(p=probs, rep=rep), open(D + '/out/venta_prob.json', 'w'), ensure_ascii=False)
print(json.dumps(rep, ensure_ascii=False, indent=1))
