import os,sqlite3,threading
from .config import settings
class AlertDeduplicator:
    def __init__(self,path=None):
        path=path or settings.db_path; os.makedirs(os.path.dirname(path) or '.',exist_ok=True)
        self.db=sqlite3.connect(path,check_same_thread=False); self.lock=threading.Lock()
        self.db.execute('CREATE TABLE IF NOT EXISTS sent_alerts(zone_id TEXT PRIMARY KEY, sent_at INTEGER NOT NULL)'); self.db.commit()
    def already_sent(self,zone_id):
        with self.lock:return self.db.execute('SELECT 1 FROM sent_alerts WHERE zone_id=?',(zone_id,)).fetchone() is not None
    def mark_sent(self,zone_id,ts):
        with self.lock:self.db.execute('INSERT OR IGNORE INTO sent_alerts(zone_id,sent_at) VALUES(?,?)',(zone_id,ts)); self.db.commit()
