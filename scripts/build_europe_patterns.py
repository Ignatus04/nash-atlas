"""Rebuild the Europe design catalogue and inline SVG recipe data.

Edit site/design/europe-patterns.json, then run this script. No image downloads.
The approved France A tile in index.html is deliberately preserved verbatim.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'site/design/europe-patterns.json'
CATALOGUE = ROOT / 'site/design/europe-patterns.md'
PAGE = ROOT / 'site/index.html'
START = '// BEGIN GENERATED EUROPE PATTERNS'
END = '// END GENERATED EUROPE PATTERNS'


def main():
    data = json.loads(SOURCE.read_text())
    entries = data['entries']
    codes = [e['code'] for e in entries]
    assert len(codes) == len(set(codes))
    meta = json.loads((ROOT / 'site/data/meta.json').read_text())
    expected = {k for k, v in meta.items() if isinstance(v, dict) and v.get('reg') == 'Europe'}
    expected |= {'AM', 'AZ', 'GE', 'KZ', 'TR'}
    assert set(codes) == expected, f'Coverage mismatch: {set(codes) ^ expected}'

    # Write the full descriptions first; the implementation follows the same source.
    lines = ['# Европейские фоны «Нашего атласа»',
             '', 'Дата: 18 ноября 2026 года. Каталог композиционных заданий и источник реализации.',
             '', '## Общий художественный язык',
             '', 'Образец — выбранный владельцем французский SVG A: редкие тонкие линейные рисунки на существующей тёмной заливке. Не карта страны, не геометрический шум и не сплошной бордюр. У каждой карточки — узнаваемая композиция из архитектуры, природы, ремёсел или повседневной культуры. Это художественная подборка, а не перечень официальных национальных символов.',
             '', 'Плитка 400 × 600, прозрачная; она повторяется по всей высоте карточки страны и её городов. Цвет линии #8fa3bf, толщина 1.2; прозрачность 0.28, у принятого французского оригинала 0.35. Без залитых силуэтов, теней, фильтров, текста, эмодзи и анимации. Большие свободные участки сохраняют читаемость. Оригинальные векторные линии, без скачанных фотографий или копирования сторонних иллюстраций.',
             '', '## Композиция и ограничения',
             '', 'Главный мотив занимает около 90 × 90 px в верхней левой части; второстепенный — около 60 × 60 справа выше центра; природный или орнаментальный — около 80 × 80 в середине справа. Ниже повторяются уменьшенные рисунки в другом повороте. Размеры ориентировочные: точные значения рецепта приведены под каждой страной. Между рисунками нет соединительных линий. На краях плитки рисунки не обрезаются: пустые верхний и нижний поля дают спокойный вертикальный стык.',
             '', 'Нельзя использовать гербы, флаги, политические лозунги, границы, портреты, карикатуры и религиозные надписи. Рисунок купола — архитектура без креста. Животные — спокойные, без агрессии. У спорных территорий только культурные и природные мотивы; оформление не утверждает статус территории. Деление на группы ниже нужно для полноты каталога, а не для определения суверенитета.',
             '', '## Охват', '', f'{len(entries)} отдельных карточек: все записи Europe из meta.json, включая острова и отдельные территории, плюс Армения, Азербайджан, Грузия, Казахстан и Турция. Отсутствующие и повторяющиеся коды проверяются генератором.', '']
    for e in entries:
        lines += [f"## {e['name']} — {e['code']}", '', e['group'] + '.', '']
        for label, m in zip(['Главный рисунок', 'Дополнительный рисунок', 'Природный / орнаментальный акцент'], e['motifs']):
            lines += [f"**{label}:** {m['description']}. Код рисунка: `{m['id']}`.", '']
        if e.get('approved'):
            lines += ['**Композиция:** исходный вариант A, выбранный владельцем. Сохраняются башни в (95, 200) и (315, 560), круассаны в (290, 120) и (60, 540), виноград в (240, 300), окно в (120, 420), мелкие акценты. Авторский SVG не перерисовывается.', '']
        else:
            lines += [f"**Композиция:** диагональный ритм A. Главный мотив — центр (90, 140), масштаб 1.9 и центр (310, 505), масштаб 1.15. Второй — (290, 115), масштаб 1.25 и (95, 405), масштаб 1.3. Третий — (260, 285), масштаб 1.65 и (65, 545), масштаб 0.9. Базовые углы −4°, 14°, −12°, 3°, 5°, −20°; индивидуальный сдвиг {e['rotation']}°. Ни один рисунок не пересекает край 400 × 600.", '']
        lines += ['**Проверка:** мотивы узнаваемы без подписи; фон остаётся слабее текста; в карточке города используется тот же набор; при прокрутке к заметкам и регионам узор продолжается; элементы не просвечивают через фотографии. Проверять на ширине 390 и 420 px, а также вертикальный стык двух плиток.', '']
    CATALOGUE.write_text('\n'.join(lines) + '\n')

    recipes = {e['code']: {'motifs': [m['id'] for m in e['motifs']], 'rotation': e['rotation']} for e in entries}
    generated = START + '\nObject.assign(NATIONAL_MARKS,' + json.dumps(data['marks'], ensure_ascii=False, separators=(',', ':')) + ');\n'
    generated += 'const EUROPE_PATTERNS=' + json.dumps(recipes, ensure_ascii=False, separators=(',', ':')) + ';\n' + END
    page = PAGE.read_text()
    if START in page:
        a, b = page.index(START), page.index(END) + len(END)
        page = page[:a] + generated + page[b:]
    else:
        page = page.replace('// France: user-approved composition A, transparent repeating tile.', generated + '\n// France: user-approved composition A, transparent repeating tile.')
    PAGE.write_text(page)
    print(f'Generated catalogue and SVG recipes for {len(entries)} cards')


if __name__ == '__main__':
    main()
