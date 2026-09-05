#!/usr/bin/env python3
"""The Hebrew ambiguous queue, commonest first, with candidates and one real context each.

The counterpart of ambiguous_queue.py. Two differences that matter, both from he_ingest:
resolutions are loaded PER TEXT (a scoped line in "@texts" wins for the texts it names), so a
surface is counted as ambiguous only where nothing has decided it; and the pointing on the page
is itself evidence, so a token that arrives pointed may already be settled.

    python3 pipeline/he_ambiguous_queue.py [count] [start]
"""
import sys
import os
import json
import glob
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'spike', 'he'))
import paths                                          # noqa: E402
paths.require('he')
import he_ingest                                      # noqa: E402
from lex import Lexicon                               # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
START = int(sys.argv[2]) if len(sys.argv) > 2 else 0

lex = Lexicon()
counts, ctx, where = collections.Counter(), {}, collections.defaultdict(collections.Counter)
ann_of = {}
for f in sorted(glob.glob('texts/he/*.json')):
    try:
        d = json.load(open(f, encoding='utf-8'))
    except Exception:
        continue
    if 'sentences' not in d:
        continue
    res = he_ingest.load_resolutions(d['id'])
    for s in d.get('sentences', []):
        # The target-language field is 'ar' in BOTH languages: the text schema is shared and
        # the LANG pack decides what it holds. Reading s['he'] here is a KeyError on every file.
        for t in he_ingest.tokenize(s['ar']):
            a = he_ingest.annotate(lex, t, res)
            if (a.get('provenance') or '').startswith('AMBIGUOUS'):
                counts[t] += 1
                ann_of.setdefault(t, a)
                where[t][d['id'].rsplit('-ch', 1)[0]] += 1
                ctx.setdefault(t, (s['ar'], s.get('en', '')))

print('%d distinct, %d tokens\n' % (len(counts), sum(counts.values())))
for i, (w, n) in enumerate(counts.most_common()[START:START + N], START + 1):
    ann = ann_of[w]
    print('%3d. %-14s %3d  %s' % (i, w, n, ctx[w][0][:60]))
    print('               %s' % ctx[w][1][:72])
    print('               in: %s' % ', '.join('%s(%d)' % kv for kv in where[w].most_common(4)))
    # The ANNOTATION's options, not lex.look()'s records. A single-candidate word can still be
    # ambiguous, because the second reading is a particle plus a different word — ליער is one
    # entry, לְיַעֵר "to afforest", and also ל- + יַעַר "to the forest", which is what every
    # sentence in the corpus means. Only annotate() assembles those alternatives, so showing
    # lex.look()'s list hides exactly the reading the adjudicator needs to pick.
    for o in (ann.get('options') or [])[:7]:
        print('       %-9s %-14s %-20s %s' % (o.get('id'), str(o.get('pointed'))[:14],
              str(o.get('analysis'))[:20], str(o.get('gloss'))[:52]))
    if ann.get('_cut_for_prompt'):
        print('       (matched after cutting %s)' % ann['_cut_for_prompt'])
    print()
