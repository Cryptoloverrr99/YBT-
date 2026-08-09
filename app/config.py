import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

def b(name, default=True): return os.getenv(name, str(default)).lower() in {'1','true','yes','on'}
def i(name, default): return int(os.getenv(name, default))
def f(name, default): return float(os.getenv(name, default))

@dataclass(frozen=True)
class Settings:
    deriv_ws_url:str=os.getenv('DERIV_WS_URL','wss://api.derivws.com/trading/v1/options/ws/public')
    telegram_bot_token:str=os.getenv('TELEGRAM_BOT_TOKEN','')
    telegram_chat_id:str=os.getenv('TELEGRAM_CHAT_ID','')
    poll_seconds:int=i('POLL_SECONDS',60)
    history_bars:int=i('HISTORY_BARS',600)
    pivot_left_bars:int=i('PIVOT_LEFT_BARS',20)
    pivot_right_bars:int=i('PIVOT_RIGHT_BARS',2)
    cluster_merge_atr:float=f('CLUSTER_MERGE_ATR',0.22)
    use_volume_weight:bool=b('USE_VOLUME_WEIGHT',True)
    use_age_weight:bool=b('USE_AGE_WEIGHT',True)
    freshness_memory_horizon:int=i('FRESHNESS_MEMORY_HORIZON',260)
    minimum_heat_score_to_show:float=f('MINIMUM_HEAT_SCORE_TO_SHOW',1.25)
    visual_saturation_score:float=f('VISUAL_SATURATION_SCORE',8.0)
    atr_length:int=i('ATR_LENGTH',14)
    base_band_height_atr:float=f('BASE_BAND_HEIGHT_ATR',0.22)
    max_zones:int=i('MAX_ZONES',12)
    pressure_span_atr:float=f('PRESSURE_SPAN_ATR',3.0)
    trend_context_length:int=i('TREND_CONTEXT_LENGTH',55)
    minimum_magnet_score:int=i('MINIMUM_MAGNET_SCORE',62)
    faded_score_factor:float=f('FADE_RETENTION_FACTOR',0.35)
    active_score_decay:float=f('ACTIVE_SCORE_DECAY',0.0)
    purge_faded_zones_after:int=i('PURGE_FADED_ZONES_AFTER',350)
    extinguish_mode:str=os.getenv('LIQUIDITY_TAKEN_BEHAVIOR','Fade')
    new_zone_alert_min_score:float=f('NEW_ZONE_ALERT_MIN_SCORE',2.0)
    alignment_tolerance_atr:float=f('ALIGNMENT_TOLERANCE_ATR',0.65)
    db_path:str=os.getenv('DB_PATH','data/alerts.sqlite3')
    timeframes:dict= None
    def __post_init__(self): object.__setattr__(self,'timeframes',{'1H':3600,'2H':7200,'3H':10800,'4H':14400})
settings=Settings()
