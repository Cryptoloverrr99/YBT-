from app.alignment import stars_for

def test_stars():
    assert stars_for(['1H'])==1
    assert stars_for(['1H','2H'])==2
    assert stars_for(['1H','2H','3H'])==3
    assert stars_for(['1H','2H','3H','4H'])==4
