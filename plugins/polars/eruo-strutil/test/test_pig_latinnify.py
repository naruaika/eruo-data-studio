from eruo_strutil import pig_latinnify
import polars


def test_pig_latinnify():
    df = polars.DataFrame(
        {
            'input': ['this', 'is', 'not', 'pig', 'latin'],
        }
    )
    result = df.with_columns(output=pig_latinnify('input'))

    expected = polars.DataFrame(
        {
            'input':  ['this', 'is', 'not', 'pig', 'latin'],
            'output': ['histay', 'siay', 'otnay', 'igpay', 'atinlay'],
        }
    )

    assert result['output'].to_list() == expected['output'].to_list()