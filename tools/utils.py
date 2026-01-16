import pymorphy3

morph = pymorphy3.MorphAnalyzer()

def _pick_gender(parses):
    for p in parses:
        g = p.tag.gender
        if g in ("femn", "masc"):
            return g
    return None

def fio_to_nominative(fio: str) -> str:
    '''Парсит ФИО в ФИО именительного падежа'''
    parts = fio.strip().split()
    if not parts:
        return fio

    parses_by_part = [morph.parse(x) for x in parts]

    gender = None
    if len(parts) >= 3:
        gender = _pick_gender(parses_by_part[2]) or _pick_gender(parses_by_part[1])
    elif len(parts) == 2:
        gender = _pick_gender(parses_by_part[1])
    else:
        gender = _pick_gender(parses_by_part[0])

    out = []
    for i, part in enumerate(parts):
        parses = parses_by_part[i]
        if not parses:
            out.append(part)
            continue
        best = parses[0]
        tag_set = set(best.tag.grammemes)
        is_fio_token = bool({'Name', 'Surn', 'Patr'} & tag_set)

        if is_fio_token:
            feats = {'nomn'}
            if gender and ('Surn' in tag_set or 'Patr' in tag_set or 'Name' in tag_set):
                feats.add(gender)
            inf = best.inflect(feats)
            w = inf.word if inf else best.normal_form
        else:
            inf = best.inflect({'nomn'})
            w = inf.word if inf else best.normal_form

        out.append(w[:1].upper() + w[1:])

    return " ".join(out)
