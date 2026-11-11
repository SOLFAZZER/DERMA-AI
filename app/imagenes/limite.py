"""Corta la recepción de cargas demasiado grandes antes de procesarlas (DERMA-SRS-6.x, error 413)."""
import json


class LimiteCuerpo:
    """Middleware ASGI: rechaza con 413 los cuerpos que superan `max_bytes` en la ruta indicada.

    Revisa el encabezado Content-Length y además cuenta los bytes que van llegando, de modo que
    deja de leer apenas se supera el límite aunque el cliente no declare el tamaño.
    """

    def __init__(self, app, ruta: str, max_bytes: int):
        self.app = app
        self.ruta = ruta
        self.max_bytes = max_bytes

    async def _responder_413(self, send) -> None:
        cuerpo = json.dumps({"detail": "La imagen supera el tamaño máximo permitido."}).encode()
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(cuerpo)).encode())]})
        await send({"type": "http.response.body", "body": cuerpo})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != self.ruta or scope["method"] != "POST":
            return await self.app(scope, receive, send)

        declarado = dict(scope["headers"]).get(b"content-length", b"")
        if declarado.isdigit() and int(declarado) > self.max_bytes:
            return await self._responder_413(send)

        total = 0
        excedido = False
        respondido = False

        async def receive_limitado():
            nonlocal total, excedido
            if excedido:
                return {"type": "http.disconnect"}
            mensaje = await receive()
            if mensaje["type"] == "http.request":
                total += len(mensaje.get("body", b""))
                if total > self.max_bytes:
                    excedido = True
                    return {"type": "http.disconnect"}
            return mensaje

        async def send_limitado(mensaje):
            nonlocal respondido
            if excedido:  # lo que responda la app se reemplaza por el 413
                if not respondido:
                    respondido = True
                    await self._responder_413(send)
                return
            await send(mensaje)

        try:
            await self.app(scope, receive_limitado, send_limitado)
        except Exception:
            if not excedido:
                raise
        if excedido and not respondido:
            await self._responder_413(send)
