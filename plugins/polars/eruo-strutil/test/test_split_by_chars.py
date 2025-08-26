from eruo_strutil import split_by_chars
import polars


def test_split_by_chars():
    actors = [
        'Nadya Arina, Refal Hady, Giorgino Abraham, Anggika Bolsterli, Laura Theux, Christine Hakim',
        'Maudy Koesnaedi, Rano Karno, Cornelia Agatha, Mandra Naih, Aminah Tjendrakasih, Suty Karno',
        'Shay Mitchell; Liza Soberano; Jon Jon Briones; Darren Criss; Manny Jacinto; Dante Basco',
    ]
    df = polars.DataFrame({'input': actors})

    series = polars.select(split_by_chars(df.get_column('input'), characters=',;')).to_series()
    result = polars.DataFrame({'output': series})

    expected = polars.DataFrame({
        'output': [
            'Nadya Arina', 'Refal Hady', 'Giorgino Abraham', 'Anggika Bolsterli', 'Laura Theux', 'Christine Hakim',
            'Maudy Koesnaedi', 'Rano Karno', 'Cornelia Agatha', 'Mandra Naih', 'Aminah Tjendrakasih', 'Suty Karno',
            'Shay Mitchell', 'Liza Soberano', 'Jon Jon Briones', 'Darren Criss', 'Manny Jacinto', 'Dante Basco',
        ]
    })

    assert result['output'].to_list() == expected['output'].to_list()