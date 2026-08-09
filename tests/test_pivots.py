from app.indicators import pivot_high,pivot_low
from app.models import Candle

def c(h,l): return Candle(0,0,h,l,0,1)
def test_right_confirmation_window():
    xs=[c(9,1),c(10,2),c(12,3),c(11,4),c(8,2)]
    assert pivot_high(xs,1,2,2)
    assert not pivot_high(xs,1,2,1)
