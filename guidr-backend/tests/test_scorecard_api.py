from src.scrapers.schools.scorecard import CollegeScorecardClient


def test_scorecard_map_row_parses_numbers():
    client = CollegeScorecardClient(api_key="test-key")
    row = {
        "id": 999,
        "latest.cost.avg_net_price.overall": "25000",
        "latest.cost.tuition.in_state": "12000",
        "latest.cost.tuition.out_of_state": "18000",
        "latest.completion.rate_suppressed": "0.8",
        "latest.earnings.10_yrs_after_entry.median": "90000",
    }
    metrics = client._map_row(row)  # type: ignore[attr-defined]
    assert metrics.unit_id == "999"
    assert metrics.average_cost == 25000
    assert metrics.graduation_rate == 0.8
