from eruo_strutil import to_sentence_case
import polars


def test_to_sentence_case():
    df = polars.DataFrame({
        'input': [
            'lorem. ipsum! dolor? sit amet.',
            'lorem.ipsum!dolor?sit amet.',
            'UPPERCASE',
            'lowercase',
            'kebab-case',
            'snake_case',
            'camelCase',
            'PascalCase',
            'CONSTANT_CASE',
            'dot.case',
            'Sentence case',
        ],
        'expected': [
            'Lorem. Ipsum! Dolor? Sit amet.',
            'Lorem.ipsum!dolor?sit amet.',
            'Uppercase',
            'Lowercase',
            'Kebab-case',
            'Snake_case',
            'Camel case',
            'Pascal case',
            'Constant_case',
            'Dot.case',
            'Sentence case',
        ],
    })
    df = df.with_columns(output=to_sentence_case('input'))

    assert df['output'].to_list() == df['expected'].to_list()