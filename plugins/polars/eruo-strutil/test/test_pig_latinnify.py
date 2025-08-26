from eruo_strutil import pig_latinnify
import polars


def test_pig_latinnify():
    df = polars.DataFrame({
        'input': [
            'he does not know',
            'this',
            'is',
            'banana',
            'black',
            'smile',
            'straight',
            'hello!',
        ],
        'expected': [
            'ehay oesday otnay owknay',
            'isthay',
            'isway',
            'ananabay',
            'ackblay',
            'ilesmay',
            'aightstray',
            'ellohay!',
        ],
    })
    df = df.with_columns(output=pig_latinnify('input'))

    assert df['output'].to_list() == df['expected'].to_list()