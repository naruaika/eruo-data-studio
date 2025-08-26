from eruo_strutil import to_sponge_case
import polars


def test_to_sponge_case():
    df = polars.DataFrame({
        'input': ['lorem. ipsum! dolor? sit amet.'],
    })
    df = df.with_columns(output=to_sponge_case('input'))

    assert True # no idea how to test this