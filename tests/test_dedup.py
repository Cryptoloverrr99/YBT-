from app.dedup import AlertDeduplicator

def test_dedup(tmp_path):
    d=AlertDeduplicator(str(tmp_path/'a.sqlite3'))
    assert not d.already_sent('x'); d.mark_sent('x',1); assert d.already_sent('x')
