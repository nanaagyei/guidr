import pandas as pd

from src.scrapers.schools.ipeds import IPEDSScraper


def test_ipeds_row_to_institution():
    scraper = IPEDSScraper()
    row = pd.Series(
        {
            "INSTNM": "Sample University",
            "CITY": "Boston",
            "STABBR": "MA",
            "WEBADDR": "www.sample.edu",
            "SECTOR": "1",
            "UNITID": "123456",
        }
    )
    institution = scraper._row_to_institution(row)  # type: ignore[attr-defined]
    assert institution is not None
    assert institution.name == "Sample University"
    assert institution.public_private == "public"
    assert institution.ipeds_unit_id == "123456"

