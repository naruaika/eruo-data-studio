from eruo_strutil import split_by_chars
import polars


def test_split_by_chars():
    input = polars.DataFrame({
        'input': [
            'Nadya Arina, Refal Hady, Giorgino Abraham, Anggika Bolsterli, Laura Theux, Christine Hakim',
            'Maudy Koesnaedi, Rano Karno, Cornelia Agatha, Mandra Naih, Aminah Tjendrakasih, Suty Karno',
            'Shay Mitchell; Liza Soberano; Jon Jon Briones; Darren Criss; Manny Jacinto; Dante Basco',
        ],
    })

    output = polars.select(split_by_chars(input.get_column('input'), characters=',;')).to_series().to_list()

    expected = [
        'Nadya Arina', 'Refal Hady', 'Giorgino Abraham', 'Anggika Bolsterli', 'Laura Theux', 'Christine Hakim',
        'Maudy Koesnaedi', 'Rano Karno', 'Cornelia Agatha', 'Mandra Naih', 'Aminah Tjendrakasih', 'Suty Karno',
        'Shay Mitchell', 'Liza Soberano', 'Jon Jon Briones', 'Darren Criss', 'Manny Jacinto', 'Dante Basco',
    ]

    assert output == expected