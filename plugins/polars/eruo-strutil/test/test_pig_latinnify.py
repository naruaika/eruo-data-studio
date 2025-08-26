from eruo_strutil import pig_latinnify
import polars


def test_pig_latinnify():
    df = polars.DataFrame(
        {
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
        }
    )
    result = df.with_columns(output=pig_latinnify('input'))

    expected = polars.DataFrame(
        {
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
            'output': [
                'ehay oesday otnay owknay',
                'isthay',
                'isway',
                'ananabay',
                'ackblay',
                'ilesmay',
                'aightstray',
                'ellohay!',
            ],
        }
    )

    assert result['output'].to_list() == expected['output'].to_list()