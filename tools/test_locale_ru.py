"""Runs WoW: Forever's own Russian (ruRU) tooltips through the addon's real parser (DoesItDie.lua with Locale.lua
and every language file the .toc loads before it) and the real name tables, and checks what the addon would track.
The tooltips are Wowhead's (tooltip API, data env Forever, locale 7), with the amounts Wowhead shows as unresolved
formulas (Immolate, Rupture, Blizzard, Rain of Fire) replaced by numbers, as the game shows them. English patterns
run first, as in game, so this also checks that they (and the other languages') never misread Russian text.
Some cases are repeated with "ё" where Wowhead prints "е" (приём, тёмной), as the client may.

    pip install lupa
    python tools/test_locale_ru.py
"""
import os
import sys

import locale  # noqa: E402
locale.setlocale(locale.LC_CTYPE, "C")  # as in WoW: Lua's %d and %s follow the C library's locale
from lupa import lua51

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.join(HERE, "..", "DoesItDie")
src = open(os.path.join(ADDON, "DoesItDie.lua"), encoding="utf-8").read()
TOC = [line.strip() for line in open(os.path.join(ADDON, "DoesItDie.toc"), encoding="utf-8")]
LOCALE_PRELUDE = "local ns = {}\n" + "".join(
    ";(function(...)\n" + open(os.path.join(ADDON, name), encoding="utf-8").read() + "\nend)(\"DoesItDie\", ns)\n"
    for name in TOC[:TOC.index("DoesItDie.lua")] if name.endswith(".lua"))


def chunk(start_marker, end_marker):
    start = src.index(start_marker)
    return src[start:src.index(end_marker, start)]


lua = lua51.LuaRuntime(unpack_returned_tuples=True)
track, locale = lua.execute("\n".join([
    LOCALE_PRELUDE,
    "local function isSecret(v) return false end",
    chunk("local DEFAULT_TICK_INTERVAL", "local TICK_MATCH_WINDOW"),
    chunk("-- Tick intervals that differ", "-- User options"),
    chunk("local function schoolFromWords",
          "---------------------------------------------------------------------------\n-- DoT tracking"),
    """
    -- onPlayerCast's decision: ignore list by the client's name, parse, interval and school by name.
    return function(name, desc, comboPoints)
        if IGNORED_SPELLS[name] then return "ignored (list)" end
        local total, school, duration, stated = parseDot(desc, comboPoints)
        if not total then return "not tracked" end
        local interval = stated or KNOWN_TICK_INTERVALS[name] or DEFAULT_TICK_INTERVAL
        school = SCHOOL_BY_NAME[name] or school
        local ticks = math.max(1, math.floor(duration / interval + 0.5))
        return string.format("%d dmg, school %d, %gs, every %gs -> %d ticks of %.1f",
            total, school, duration, interval, ticks, total / ticks)
    end, ns.locale
    """,
]))

RIP = ('Завершающий прием, наносящий периодический урон. Урон увеличивается за счет длины серии и силы атаки:\n'
       ' 1 прием: 57 ед. урона за 12 сек.\n 2 приема: 90 ед. урона за 12 сек.\n 3 приема: 123 ед. урона за 12 сек.\n'
       ' 4 приема: 156 ед. урона за 12 сек.\n 5 приемов: 189 ед. урона за 12 сек.')
RUPTURE = ('Завершающий прием, наносящий периодический урон, который увеличивается за счет силы атаки. Время действия '
           'зависит от длины серии:\n 1 прием: 25 ед. урона за 8 сек.\n 2 приема: 37 ед. урона за 10 сек.\n'
           ' 3 приема: 51 ед. урона за 12 сек.\n 4 приема: 68 ед. урона за 14 сек.\n 5 приемов: 87 ед. урона за 16 сек.')
RAKE = ('Наносит противнику глубокую рану. Противник теряет 27 и дополнительно 60 здоровья за 9 сек. в результате '
        'кровотечения. Длина серии приемов увеличивается на 1.')

# (spell id, name, tooltip, combo points or None, expected tracking result)
CASES = [
    (172, 'Порча',
     'Порча цели с нанесением ей 40 ед. урона от темной магии за 12 сек.',
     None, '40 dmg, school 32, 12s, every 3s -> 4 ticks of 10.0'),
    (172, 'Порча',
     'Порча цели с нанесением ей 40 ед. урона от тёмной магии за 12 сек.',
     None, '40 dmg, school 32, 12s, every 3s -> 4 ticks of 10.0'),
    (348, 'Жертвенный огонь',
     'Наносит противнику 11 ед. урона от огня сразу и еще 15 ед. урона от огня за 15 сек.',
     None, '15 dmg, school 4, 15s, every 3s -> 5 ticks of 3.0'),
    (589, 'Слово Тьмы: Боль',
     'Слово Тьмы, наносящее 30 ед. урона от темной магии за 18 сек.',
     None, '30 dmg, school 32, 18s, every 3s -> 6 ticks of 5.0'),
    (2944, 'Всепожирающая чума',
     'Болезнь, наносящая 128 ед. урона от темной магии в течение 24 сек. Исцеление применяющего заклинание за счет нанесенного урона.',
     None, '128 dmg, school 32, 24s, every 3s -> 8 ticks of 16.0'),
    (8921, 'Лунный огонь',
     'Обжигает противника, нанося ему 10 в 12 ед. урона от тайной магии и 12 дополнительного урона от тайной магии в течение 9 сек.',
     None, '12 dmg, school 64, 9s, every 3s -> 3 ticks of 4.0'),
    (5570, 'Рой насекомых',
     'Противника атакует рой насекомых, снижающий его вероятность попадания атаками на 2% и наносящий 48 ед. урона от сил природы за 12 сек.',
     None, '48 dmg, school 8, 12s, every 2s -> 6 ticks of 8.0'),
    (980, 'Бич агонии',
     'Цель бьется в агонии, получая 72 ед. урона от темной магии за 24 сек. Урон увеличивается постепенно и достигает своего пика к концу действия "Бича". Каждый чернокнижник может применить к каждой цели только одно заклинание категории "Бич".',
     None, '72 dmg, school 32, 24s, every 2s -> 12 ticks of 6.0'),
    (14914, 'Священный огонь',
     'Навлечение на противника священного пламени, которое наносит 53 в 65 ед. урона от светлой магии и дополнительно 20 ед. урона от светлой магии в течение 10 сек.',
     None, '20 dmg, school 2, 10s, every 2s -> 5 ticks of 4.0'),
    (133, 'Огненный шар',
     'Бросок огненного шара, который наносит 15 в 23 ед. урона от огня единовременно и 2 ед. урона от огня в течение 4 сек.',
     None, '2 dmg, school 4, 4s, every 2s -> 2 ticks of 1.0'),
    (11366, 'Огненная глыба',
     'Бросок огромной огненной глыбы, которая наносит 101 в 131 ед. урона от огня единовременно и 44 ед. урона от огня в течение 12 сек.',
     None, '44 dmg, school 4, 12s, every 3s -> 4 ticks of 11.0'),
    (8050, 'Огненный шок',
     'Мгновенное обжигание противника огнем, с нанесением 29 ед. урона от огня немедленно и 28 ед. урона от огня в течение 12 сек.',
     None, '28 dmg, school 4, 12s, every 3s -> 4 ticks of 7.0'),
    (8052, 'Огненный шок',
     'Мгновенное обжигание противника огнем, с нанесением 56 ед. урона от огня немедленно и 48 ед. урона от огня в течение 12 сек.',
     None, '48 dmg, school 4, 12s, every 3s -> 4 ticks of 12.0'),
    (339, 'Гнев деревьев',
     'Оплетает цель корнями, обездвиживая и нанося 20 ед. урона от сил природы за 12 сек. Урон может снять эффект. Одновременно вы можете обездвижить [Разрастание: не более 3 целей / только одну цель].',
     None, '20 dmg, school 8, 12s, every 3s -> 4 ticks of 5.0'),
    (1978, 'Укус змеи',
     'Укус, наносящий 15 ед. урона от сил природы в течение 15 сек. На каждую цель может действовать только один "Укус" каждого охотника единовременно.',
     None, '15 dmg, school 8, 15s, every 3s -> 5 ticks of 3.0'),
    (13795, 'Обжигающая ловушка',
     'Устанавливает огненную ловушку, которая обжигает первого приблизившегося к ней противника, нанося ему 105 ед. урона от огня за 15 сек. Ловушка существует 1 мин. Единовременно может быть установлена только одна огненная ловушка.',
     None, '105 dmg, school 4, 15s, every 3s -> 5 ticks of 21.0'),
    (1822, 'Глубокая рана', RAKE,
     None, '60 dmg, school 1, 9s, every 3s -> 3 ticks of 20.0'),
    (703, 'Гаррота',
     'Удушающий прием, наносящий противнику 144 ед. урона за 18 сек. Прием увеличивает силу вашей атаки. Для выполнения приема необходимо находиться за спиной цели в состоянии незаметности. Длина серии приемов увеличивается на 1.',
     None, '144 dmg, school 1, 18s, every 3s -> 6 ticks of 24.0'),
    (772, 'Кровопускание',
     'Наносит цели кровоточащую рану, из-за которой она теряет 15 ед. здоровья за 9 сек.',
     None, '15 dmg, school 1, 9s, every 3s -> 3 ticks of 5.0'),
    (9005, 'Наскок',
     'Наброситься на противника, оглушая его на 2 сек. и нанося 114 ед. урона за 18 сек. Чтобы применить этот прием, друид должен красться и находиться за спиной цели. Длина серии приемов увеличивается на 1.',
     None, '114 dmg, school 1, 18s, every 3s -> 6 ticks of 19.0'),
    (18265, 'Вытягивание жизни',
     'Вы похищаете у цели 11 ед. здоровья раз в 3 сек. и восполняете себе здоровье в том же объеме. Время действия – 30 сек.',
     None, '110 dmg, school 32, 30s, every 3s -> 10 ticks of 11.0'),
    (1079, 'Разорвать', RIP, 5, '189 dmg, school 1, 12s, every 2s -> 6 ticks of 31.5'),
    (1079, 'Разорвать', RIP, 1, '57 dmg, school 1, 12s, every 2s -> 6 ticks of 9.5'),
    (1079, 'Разорвать', RIP.replace('прием', 'приём'), 3, '123 dmg, school 1, 12s, every 2s -> 6 ticks of 20.5'),
    (1943, 'Рваная рана', RUPTURE, 5, '87 dmg, school 1, 16s, every 2s -> 8 ticks of 10.9'),
    (1943, 'Рваная рана', RUPTURE, 1, '25 dmg, school 1, 8s, every 2s -> 4 ticks of 6.2'),
    (139, 'Обновление',
     'Излечение цели на 45 ед. в течение 15 сек.',
     None, 'not tracked'),
    (774, 'Омоложение',
     'Излечение цели на 32 ед. в течение 12 сек.',
     None, 'not tracked'),
    (2823, 'Смертельный яд',
     'Смазать оружие ядом, действующим в течение 30 мин.\nКаждый удар с вероятностью 30% отравляет противника ядом, наносящим 24 ед. урона от сил природы за 12 сек. Суммируется на каждой цели до 5 раз. Количество зарядов – 90.',
     None, 'not tracked'),
    (8679, 'Быстродействующий яд',
     'Смазать оружие ядом, действующим в течение 30 мин.\nКаждый удар с вероятностью 20% отравляет противника, мгновенно нанося 13 в 17 ед. урона от сил природы. Количество зарядов – 60.',
     None, 'not tracked'),
    (1752, 'Коварный удар',
     'Мгновенный удар, наносящий 3 ед. урона сверх базового урона оружия. Длина серии приемов увеличивается на 1.',
     None, 'not tracked'),
    (1082, 'Когти',
     'Рвет противника когтями, нанося 27% базового и 1 ед. дополнительного урона. Длина серии приемов увеличивается на 1.',
     None, 'not tracked'),
    (603, 'Бич судьбы',
     'Проклинает цель, нанося ей 1742 ед. урона от темной магии через 1 мин. Если цель погибает от этого заклинания, с некоторой вероятностью призывает стража ужаса. Нельзя применить к игрокам. Одновременно на цель может действовать только одно заклинание категории "Бич" каждого чернокнижника.',
     None, 'not tracked'),
    (1495, 'Укус мангуста',
     'Проводит контратаку, нанося противнику урон от оружия ближнего боя и еще 15 ед. Можно применить только после уклонения.',
     None, 'not tracked'),
    (10, 'Снежная буря',
     'Осыпает выбранную область ледяными осколками, нанося 196 ед. урона от магии льда за 8 сек.',
     None, 'ignored (list)'),
    (5740, 'Огненный ливень',
     'Призывает огненный ливень, наносящий противникам в области действия 166 ед. урона от огня за 8 сек.',
     None, 'ignored (list)'),
    (1949, 'Адское Пламя',
     'Погружает заклинателя и находящихся рядом с ним противников в волны пламени, наносящие заклинателю 86 ед. урона от огня, а его противникам – 86 ед. урона от огня раз в 1 сек. Время действия – 15 сек.',
     None, 'ignored (list)'),
    (2120, 'Огненный столб',
     'Вы призываете огненный столб, наносящий противникам в области действия 55 в 71 ед. урона от огня сразу и еще 44 ед. урона от огня за 8 сек. Одновременно может действовать только один "Огненный столб" каждого мага.',
     None, 'ignored (list)'),
    (26573, 'Освящение',
     'Вы освящаете землю у себя под ногами, нанося противникам в области действия 16 ед. урона от светлой магии за 8 сек. Наносит 4 первым противникам в области действия еще 32 ед. урона за 8 сек.',
     None, 'ignored (list)'),
    (16914, 'Гроза',
     'Создает в указанной области сильную бурю, которая наносит противникам 69 ед. урона от сил природы раз в 1 сек. и увеличивает интервал между атаками на 20%. Время действия – 10 сек. Друид должен поддерживать заклинание.',
     None, 'ignored (list)'),
    (1510, 'Град стрел',
     'Непрерывно обстреливает указанную область снарядами, наносящими противникам в радиусе 8 м 70 ед. урона от тайной магии раз в 1 сек. в течение 6 сек.',
     None, 'ignored (list)'),
    (689, 'Похищение жизни',
     'Вы похищаете у цели 10 ед. здоровья раз в 1 сек. и восполняете себе здоровье в том же объеме. Время действия – 5 сек.',
     None, 'ignored (list)'),
    (1120, 'Похищение души',
     'Похищает душу цели, нанося 85 ед. урона от темной магии за 15 сек. Когда "Похищение души" наносит урон представляющему угрозу противнику, вы с некоторой вероятностью получаете осколок души.',
     None, 'ignored (list)'),
    (5138, 'Похищение маны',
     'Вы похищаете у цели 44 ед. маны раз в 1 сек. и восполняете ману в том же объеме. Время действия – 5 сек.',
     None, 'ignored (list)'),
    (755, 'Канал здоровья',
     'Передает прислужнику 12 ед. здоровья раз в сек. в течение 10 сек. Требуется поддержание заклинания. Создает сниженный уровень угрозы.',
     None, 'ignored (list)'),
    (15407, 'Пытка разума',
     'Поражает разум противника энергией Тьмы, наносящей 63 ед. урона от темной магии за 3 сек. и снижающей скорость передвижения цели на 50%.',
     None, 'ignored (list)'),
    (5143, 'Чародейские снаряды',
     'Атака противника чародейскими снарядами, наносящими 25 ед. урона от тайной магии раз в секунду в течение 3 сек.',
     None, 'ignored (list)'),
    (10797, 'Звездные осколки',
     'На голову противника сыплются звездные осколки, нанося 162 ед. урона от тайной магии в течение 6 сек.',
     None, 'ignored (list)'),
    (13813, 'Взрывная ловушка',
     'Устанавливает огненную ловушку, которая взрывается при приближении к ней противника, нанося целям в радиусе 10 м 105 в 135 ед. урона от огня сразу и еще 150 ед. урона от огня за 20 сек. Ловушка существует 1 мин.',
     None, 'ignored (list)'),
]

# Combo points, finishers and number formats the cases above don't cover.
EXTRA = [
    ('combo awarded (Rake)', locale.comboPointsAwarded(RAKE), 1),
    ('combo awarded (Rake, приёмов)', locale.comboPointsAwarded(RAKE.replace('приемов', 'приёмов')), 1),
    ('no combo line (Corruption)', locale.comboPointsAwarded('Порча цели с нанесением ей 40 ед. урона от темной магии за 12 сек.'), None),
    ('finisher (Rip)', locale.isFinisher(RIP), True),
    ('finisher (Rip, приём)', locale.isFinisher(RIP.replace('прием', 'приём')), True),
    ('not a finisher (Rake)', locale.isFinisher(RAKE), False),
    ('decimal comma duration', track('Порча', 'Порча цели с нанесением ей 40 ед. урона от темной магии за 10,5 сек.', None),
     '40 dmg, school 32, 10.5s, every 3s -> 4 ticks of 10.0'),
    ('thousands with a space', track('Порча', 'Порча цели с нанесением ей 1 200 ед. урона от темной магии за 12 сек.', None),
     '1200 dmg, school 32, 12s, every 3s -> 4 ticks of 300.0'),
    ('thousands with a no-break space', track('Порча', 'Порча цели с нанесением ей 1\xa0200 ед. урона от темной магии за 12 сек.', None),
     '1200 dmg, school 32, 12s, every 3s -> 4 ticks of 300.0'),
]

if __name__ == "__main__":
    failures = 0
    sys.stdout.reconfigure(encoding="utf-8")
    width = max(len(c[1]) for c in CASES)
    for spell_id, name, desc, cp, expect in CASES:
        got = track(name, desc, cp)
        ok = got == expect
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {spell_id:>6} {name:<{width}}  {got}" + ("" if ok else f"   (expected {expect})"))
    print()
    for label, got, expect in EXTRA:
        ok = got == expect
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:<34} {got}" + ("" if ok else f"   (expected {expect})"))
    print()
    print("all passed" if not failures else f"{failures} FAILED")
    sys.exit(1 if failures else 0)
