from eruo_strutil import to_sentence_case
import polars


def test_to_sponge_case():
    df = polars.DataFrame(
        {
            'input': ['lorem. ipsum! dolor? sit amet.'],
        }
    )
    result = df.with_columns(output=to_sentence_case('input'))

    expected = polars.DataFrame(
        {
            'input':  ['lorem. ipsum! dolor? sit amet.'],
            'output': ['lorEm. IPsum! Dolor? sIt AmeT.'],
        }
    )

    assert result['output'].to_list() != expected['output'].to_list()