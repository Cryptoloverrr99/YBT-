import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import websockets


class DerivPublicClient:
    """
    Client public Deriv pour :
    - récupérer les symboles actifs
    - récupérer les bougies historiques
    - réutiliser UNE connexion WebSocket
    - éviter les erreurs HTTP 429
    - convertir automatiquement H1/H2/H3/H4 en secondes
    """

    DEFAULT_WS_BASE = "wss://ws.derivws.com/websockets/v3"

    TIMEFRAME_TO_SECONDS = {
        "1m": 60,
        "2m": 120,
        "3m": 180,
        "5m": 300,
        "10m": 600,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "2h": 7200,
        "3h": 10800,
        "4h": 14400,
        "8h": 28800,
        "1d": 86400,

        # variantes majuscules
        "1M": 60,
        "2M": 120,
        "3M": 180,
        "5M": 300,
        "10M": 600,
        "15M": 900,
        "30M": 1800,
        "1H": 3600,
        "2H": 7200,
        "3H": 10800,
        "4H": 14400,
        "8H": 28800,
        "1D": 86400,
    }

    def __init__(self) -> None:
        self.app_id = os.getenv("DERIV_APP_ID", "").strip()

        # Permet de conserver une URL personnalisée si elle existe.
        configured_url = os.getenv("DERIV_WS_URL", "").strip()

        if configured_url:
            self.url = configured_url
        else:
            if self.app_id:
                self.url = f"{self.DEFAULT_WS_BASE}?app_id={self.app_id}"
            else:
                self.url = self.DEFAULT_WS_BASE

        self.ws: Optional[Any] = None
        self._connect_lock = asyncio.Lock()
        self._request_lock = asyncio.Lock()
        self._req_id = 0

    # ------------------------------------------------------------------
    # TIMEFRAME
    # ------------------------------------------------------------------

    @classmethod
    def normalize_granularity(cls, timeframe: Any) -> int:
        """
        Transforme :
            1H -> 3600
            2H -> 7200
            3H -> 10800
            4H -> 14400

        Accepte également directement une valeur entière en secondes.
        """

        if isinstance(timeframe, bool):
            raise ValueError("Invalid timeframe: boolean value")

        if isinstance(timeframe, int):
            seconds = timeframe

        elif isinstance(timeframe, float):
            if not timeframe.is_integer():
                raise ValueError(
                    f"Invalid granularity: {timeframe}"
                )
            seconds = int(timeframe)

        else:
            value = str(timeframe).strip()

            if value in cls.TIMEFRAME_TO_SECONDS:
                seconds = cls.TIMEFRAME_TO_SECONDS[value]
            else:
                lower_value = value.lower()

                if lower_value in cls.TIMEFRAME_TO_SECONDS:
                    seconds = cls.TIMEFRAME_TO_SECONDS[lower_value]
                else:
                    # Accepte "3600" sous forme de texte.
                    try:
                        seconds = int(value)
                    except ValueError as exc:
                        raise ValueError(
                            f"Unsupported timeframe/granularity: {timeframe}"
                        ) from exc

        if seconds <= 0:
            raise ValueError(
                f"Granularity must be positive: {seconds}"
            )

        return seconds

    # ------------------------------------------------------------------
    # CONNECTION
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """
        Ouvre une seule connexion WebSocket et la conserve.
        """

        async with self._connect_lock:
            if self.ws is not None:
                try:
                    if not self.ws.closed:
                        return
                except Exception:
                    pass

            self.ws = await websockets.connect(
                self.url,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
                max_size=8_000_000,
            )

    async def close(self) -> None:
        """
        Ferme proprement la connexion.
        """

        if self.ws is not None:
            try:
                await self.ws.close()
            except Exception:
                pass
            finally:
                self.ws = None

    # ------------------------------------------------------------------
    # REQUEST
    # ------------------------------------------------------------------

    async def _request(
        self,
        payload: Dict[str, Any],
        retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Envoie une requête sur la connexion persistante.

        Une seule requête est traitée à la fois afin d'éviter que les
        réponses WebSocket soient mélangées.
        """

        async with self._request_lock:

            last_error: Optional[Exception] = None

            for attempt in range(retries):
                try:
                    await self.connect()

                    if self.ws is None:
                        raise RuntimeError(
                            "Deriv WebSocket connection is unavailable"
                        )

                    self._req_id += 1

                    request = dict(payload)
                    request["req_id"] = self._req_id

                    await self.ws.send(json.dumps(request))

                    while True:
                        raw = await self.ws.recv()

                        if isinstance(raw, bytes):
                            raw = raw.decode("utf-8")

                        data = json.loads(raw)

                        # On ignore les messages qui ne correspondent
                        # pas à notre requête.
                        response_req_id = data.get("req_id")

                        if (
                            response_req_id is not None
                            and response_req_id != self._req_id
                        ):
                            continue

                        if "error" in data:
                            error = data["error"]

                            message = error.get(
                                "message",
                                "Deriv API error",
                            )

                            code = error.get("code", "")

                            if code:
                                raise RuntimeError(
                                    f"{code}: {message}"
                                )

                            raise RuntimeError(message)

                        return data

                except (
                    websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.ConnectionClosedError,
                    websockets.exceptions.ConnectionClosedOK,
                    asyncio.TimeoutError,
                    OSError,
                ) as exc:

                    last_error = exc

                    await self.close()

                    # Petit délai avant reconnexion.
                    await asyncio.sleep(
                        min(2 ** attempt, 5)
                    )

                except RuntimeError:
                    # Les erreurs API ne doivent pas provoquer
                    # automatiquement une boucle infinie.
                    raise

                except Exception as exc:
                    last_error = exc
                    await self.close()

                    if attempt < retries - 1:
                        await asyncio.sleep(
                            min(2 ** attempt, 5)
                        )

            raise RuntimeError(
                f"Deriv request failed after {retries} attempts: "
                f"{last_error}"
            )

    # ------------------------------------------------------------------
    # ACTIVE SYMBOLS
    # ------------------------------------------------------------------

    async def active_symbols(self) -> List[Dict[str, Any]]:
        """
        Retourne les marchés actifs disponibles sur Deriv.
        """

        data = await self._request(
            {
                "active_symbols": "full",
                "product_type": "basic",
            }
        )

        symbols = data.get("active_symbols", [])

        if not isinstance(symbols, list):
            return []

        return symbols

    # ------------------------------------------------------------------
    # CANDLES
    # ------------------------------------------------------------------

    async def candles(
        self,
        symbol: str,
        granularity: Any,
        count: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Récupère les bougies historiques d'un symbole.

        Exemple :

            candles("frxEURUSD", "1H", 500)

        devient automatiquement :

            granularity = 3600
        """

        if not symbol:
            raise ValueError("Symbol cannot be empty")

        seconds = self.normalize_granularity(granularity)

        if count <= 0:
            raise ValueError(
                f"count must be positive: {count}"
            )

        # Deriv impose des limites raisonnables sur count.
        count = min(int(count), 5000)

        request = {
            "ticks_history": str(symbol),
            "end": "latest",
            "count": count,
            "granularity": seconds,
            "style": "candles",
        }

        data = await self._request(request)

        candles = data.get("candles", [])

        if not isinstance(candles, list):
            return []

        # Normalisation des valeurs numériques.
        result: List[Dict[str, Any]] = []

        for candle in candles:
            try:
                result.append(
                    {
                        "epoch": int(candle["epoch"]),
                        "open": float(candle["open"]),
                        "high": float(candle["high"]),
                        "low": float(candle["low"]),
                        "close": float(candle["close"]),
                    }
                )
            except (KeyError, TypeError, ValueError):
                # Une bougie invalide ne doit pas faire tomber
                # tout le scanner.
                continue

        return result

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    async def ping(self) -> bool:
        """
        Teste la connexion Deriv.
        """

        try:
            data = await self._request({"ping": 1})
            return data.get("msg_type") == "ping"
        except Exception:
            return False

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
