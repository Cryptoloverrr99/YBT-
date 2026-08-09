def test_import():
    from app.api import app
    assert app.title.startswith('Deriv YBT')
