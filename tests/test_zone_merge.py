from app.zone_engine import YBTZoneEngine
from app.config import settings
from app.models import Candle

def test_engine_constructs():
    e=YBTZoneEngine(settings); assert e.s.pivot_right_bars==2
