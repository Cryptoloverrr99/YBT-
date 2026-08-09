import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import websockets


class DerivPublicClient:
    """
    Client public Deriv.

    Fonctions :
    - récupération des symboles actifs
    - récupération des bougies historiques
    - connexion WebSocket persistante
    - limitation des reconnexions
    - gestion des erreurs 429 / connexions fermées
    - conversion automatique des timeframes en secondes
    - aucune authentification nécessaire pour les données publiques
    """

    # Endpoint PUBLIC Deriv.
    #
    # IMPORTANT :
    # Nous n'ajoutons PAS app_id à cette URL.
    # active_symbols et ticks_history sont des endpoints
    # de données publiques.
    DEFAULT_WS_URL = "wss://ws.binaryws.com/websockets/v3"

    # Timeframes acceptés par l'application.
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
        "6h": 21600,
        "8h": 28800,
        "12h": 43200,
        "1d": 86400,

        # Majuscules
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
        "6H": 21600,
        "8H": 28800,
        "12H": 43200,
        "1D": 86400,
    }

    # Granularités valides utilisées par le scanner.
    # Deriv attend une granularité en secondes.
    VALID_GRANULARITIES = {
        60,
        120,
        180,
        300,
        600,
        900,
        1800,
        3600,
        7200,
        10800,
        14400,
        21600,
        28800,
        43200,
        86400,
    }

    def __init__(self) -> None:
        """
        Initialise le client.

        DERIV_WS_URL peut éventuellement être utilisé pour
        fournir une URL personnalisée.

        Pour éviter les anciens problèmes de 401, l'URL par défaut
        reste toujours l'endpoint public.
        """

        configured_url = os.getenv("DERIV_WS_URL", "").strip()

        if configured_url:
            self.url = configured_url
        else:
            self.url = self.DEFAULT_WS_URL

        self.ws: Optional[Any] = None

        # Empêche plusieurs connexions simultanées.
        self._connect_lock = asyncio.Lock()

        # Empêche plusieurs requêtes simultanées sur la même
        # connexion et donc les réponses mélangées.
        self._request_lock = asyncio.Lock()

        self._req_id = 0

    # ================================================================
    # TIMEFRAME / GRANULARITY
    # ================================================================

    @classmethod
    def normalize_granularity(cls, timeframe: Any) -> int:
        """
        Convertit un timeframe en secondes.

        Exemples :

            "1m"  -> 60
            "15m" -> 900
            "1h"  -> 3600
            "2h"  -> 7200
            "3h"  -> 10800
            "4h"  -> 14400

        Accepte également directement :
            3600
            "3600"
        """

        if timeframe is None:
            raise ValueError("Granularity cannot be None")

        if isinstance(timeframe, bool):
            raise ValueError(
                "Invalid granularity: boolean value"
            )

        # ------------------------------------------------------------
        # Entier
        # ------------------------------------------------------------

        if isinstance(timeframe, int):
            seconds = timeframe

        # ------------------------------------------------------------
        # Float
        # ------------------------------------------------------------

        elif isinstance(timeframe, float):

            if not timeframe.is_integer():
                raise ValueError(
                    f"Invalid granularity: {timeframe}"
                )

            seconds = int(timeframe)

        # ------------------------------------------------------------
        # Texte
        # ------------------------------------------------------------

        else:

            value = str(timeframe).strip()

            if not value:
                raise ValueError(
                    "Granularity cannot be empty"
                )

            # Correspondance directe.
            if value in cls.TIMEFRAME_TO_SECONDS:
                seconds = cls.TIMEFRAME_TO_SECONDS[value]

            else:

                # Correspondance insensible à la casse.
                lower_value = value.lower()

                if lower_value in cls.TIMEFRAME_TO_SECONDS:
                    seconds = cls.TIMEFRAME_TO_SECONDS[
                        lower_value
                    ]

                else:

                    # Exemple : "3600"
                    try:
                        seconds = int(value)

                    except ValueError as exc:
                        raise ValueError(
                            f"Unsupported timeframe/granularity: "
                            f"{timeframe}"
                        ) from exc

        # ------------------------------------------------------------
        # Validation
        # ------------------------------------------------------------

        if seconds <= 0:
            raise ValueError(
                f"Granularity must be positive: {seconds}"
            )

        # Deriv ne doit recevoir que les granularités supportées
        # par notre scanner.
        if seconds not in cls.VALID_GRANULARITIES:
            raise ValueError(
                f"Unsupported Deriv granularity: {seconds} seconds"
            )

        return seconds

    # ================================================================
    # CONNECTION
    # ================================================================

    async def connect(self) -> None:
        """
        Ouvre une connexion WebSocket publique persistante.

        Une seule connexion est utilisée par le client.
        """

        async with self._connect_lock:

            # Connexion déjà active.
            if self.ws is not None:

                try:

                    if not self.ws.closed:
                        return

                except Exception:
                    pass

            self.ws = None

            # --------------------------------------------------------
            # Connexion
            # --------------------------------------------------------

            self.ws = await websockets.connect(
                self.url,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
                max_size=8_000_000,
                open_timeout=20,
            )

    async def close(self) -> None:
        """
        Ferme proprement la connexion.
        """

        ws = self.ws
        self.ws = None

        if ws is not None:

            try:
                await ws.close()

            except Exception:
                pass

    # ================================================================
    # REQUEST
    # ================================================================

    async def _request(
        self,
        payload: Dict[str, Any],
        retries: int = 4,
    ) -> Dict[str, Any]:
        """
        Envoie une requête à Deriv.

        Une seule requête à la fois est autorisée afin de garantir
        que les réponses correspondent bien au req_id envoyé.

        En cas de coupure WebSocket :
            connexion -> requête -> reconnexion -> retry
        """

        async with self._request_lock:

            last_error: Optional[Exception] = None

            for attempt in range(retries):

                try:

                    # ------------------------------------------------
                    # Connexion
                    # ------------------------------------------------

                    await self.connect()

                    if self.ws is None:
                        raise RuntimeError(
                            "Deriv WebSocket connection unavailable"
                        )

                    # ------------------------------------------------
                    # Request ID
                    # ------------------------------------------------

                    self._req_id += 1
                    request_id = self._req_id

                    request = dict(payload)
                    request["req_id"] = request_id

                    # ------------------------------------------------
                    # Envoi
                    # ------------------------------------------------

                    await self.ws.send(
                        json.dumps(request)
                    )

                    # ------------------------------------------------
                    # Réception
                    # ------------------------------------------------

                    while True:

                        raw = await self.ws.recv()

                        if isinstance(raw, bytes):
                            raw = raw.decode("utf-8")

                        data = json.loads(raw)

                        # ------------------------------------------------
                        # Ignore les messages d'un autre request.
                        # ------------------------------------------------

                        response_req_id = data.get("req_id")

                        if (
                            response_req_id is not None
                            and response_req_id != request_id
                        ):
                            continue

                        # ------------------------------------------------
                        # Erreur Deriv
                        # ------------------------------------------------

                        if "error" in data:

                            error = data.get(
                                "error",
                                {},
                            )

                            code = error.get(
                                "code",
                                "DERIV_ERROR",
                            )

                            message = error.get(
                                "message",
                                "Deriv API error",
                            )

                            raise RuntimeError(
                                f"{code}: {message}"
                            )

                        return data

                # --------------------------------------------------------
                # WebSocket fermé
                # --------------------------------------------------------

                except (
                    websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.ConnectionClosedError,
                    websockets.exceptions.ConnectionClosedOK,
                    asyncio.TimeoutError,
                    OSError,
                ) as exc:

                    last_error = exc

                    await self.close()

                    if attempt < retries - 1:

                        # Backoff progressif :
                        # 1s -> 2s -> 4s
                        delay = min(
                            2 ** attempt,
                            5,
                        )

                        await asyncio.sleep(delay)

                # --------------------------------------------------------
                # Erreurs WebSocket HTTP (401 / 429 / etc.)
                # --------------------------------------------------------

                except websockets.exceptions.InvalidStatus as exc:

                    last_error = exc

                    await self.close()

                    # Pour un 401, reconnecter sans fin ne sert à rien.
                    # Le problème est généralement l'URL ou
                    # l'authentification.
                    status_code = getattr(
                        exc,
                        "status_code",
                        None,
                    )

                    if status_code == 401:
                        raise RuntimeError(
                            "Deriv WebSocket returned HTTP 401 "
                            "(Unauthorized). "
                            "Check DERIV_WS_URL in Render. "
                            "For public market data, use: "
                            "wss://ws.binaryws.com/websockets/v3 "
                            "without app_id."
                        ) from exc

                    # Pour 429, on attend plus longtemps.
                    if status_code == 429:

                        delay = min(
                            5 * (attempt + 1),
                            20,
                        )

                    else:

                        delay = min(
                            2 ** attempt,
                            10,
                        )

                    if attempt < retries - 1:
                        await asyncio.sleep(delay)

                # --------------------------------------------------------
                # Erreur API Deriv
                # --------------------------------------------------------

                except RuntimeError:

                    # Les erreurs retournées directement par l'API
                    # ne doivent pas provoquer une reconnexion inutile.
                    raise

                # --------------------------------------------------------
                # Autre erreur
                # --------------------------------------------------------

                except Exception as exc:

                    last_error = exc

                    await self.close()

                    if attempt < retries - 1:

                        delay = min(
                            2 ** attempt,
                            5,
                        )

                        await asyncio.sleep(delay)

            raise RuntimeError(
                f"Deriv request failed after "
                f"{retries} attempts: {last_error}"
            )

    # ================================================================
    # ACTIVE SYMBOLS
    # ================================================================

    async def active_symbols(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Retourne les symboles actifs disponibles.

        Aucune authentification n'est nécessaire.
        """

        data = await self._request(
            {
                "active_symbols": "full",
                "product_type": "basic",
            }
        )

        symbols = data.get(
            "active_symbols",
            [],
        )

        if not isinstance(symbols, list):
            return []

        return symbols

    # ================================================================
    # CANDLES
    # ================================================================

    async def candles(
        self,
        symbol: str,
        granularity: Any,
        count: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Récupère les bougies historiques.

        Exemple :

            await client.candles(
                "1HZ100V",
                "1H",
                500
            )

        Le "1H" est automatiquement transformé en 3600.
        """

        # ------------------------------------------------------------
        # Symbol
        # ------------------------------------------------------------

        if not symbol:
            raise ValueError(
                "Symbol cannot be empty"
            )

        symbol = str(symbol).strip()

        # ------------------------------------------------------------
        # Granularity
        # ------------------------------------------------------------

        seconds = self.normalize_granularity(
            granularity
        )

        # ------------------------------------------------------------
        # Count
        # ------------------------------------------------------------

        try:
            count = int(count)

        except (TypeError, ValueError) as exc:

            raise ValueError(
                f"Invalid candle count: {count}"
            ) from exc

        if count <= 0:
            raise ValueError(
                f"count must be positive: {count}"
            )

        # Limite de sécurité.
        count = min(count, 5000)

        # ------------------------------------------------------------
        # Requête
        # ------------------------------------------------------------

        request = {
            "ticks_history": symbol,
            "end": "latest",
            "count": count,
            "granularity": seconds,
            "style": "candles",
        }

        data = await self._request(
            request
        )

        # ------------------------------------------------------------
        # Candles
        # ------------------------------------------------------------

        candles = data.get(
            "candles",
            [],
        )

        if not isinstance(candles, list):
            return []

        result: List[Dict[str, Any]] = []

        # ------------------------------------------------------------
        # Normalisation
        # ------------------------------------------------------------

        for candle in candles:

            try:

                result.append(
                    {
                        "epoch": int(
                            candle["epoch"]
                        ),
                        "open": float(
                            candle["open"]
                        ),
                        "high": float(
                            candle["high"]
                        ),
                        "low": float(
                            candle["low"]
                        ),
                        "close": float(
                            candle["close"]
                        ),
                    }
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ):

                # Une bougie incorrecte ne doit pas faire
                # planter tout le scanner.
                continue

        return result

    # ================================================================
    # PING
    # ================================================================

    async def ping(self) -> bool:
        """
        Teste la connexion publique Deriv.
        """

        try:

            data = await self._request(
                {"ping": 1}
            )

            return data.get(
                "msg_type"
            ) == "ping"

        except Exception:

            return False

    # ================================================================
    # CONTEXT MANAGER
    # ================================================================

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        await self.close()
