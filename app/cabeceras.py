"""Cabeceras de seguridad HTTP para todas las respuestas."""

CSP = (b"default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; "
       b"connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
SIN_CSP = ("/docs", "/redoc", "/openapi.json")  # la documentación interactiva de FastAPI usa recursos externos


class CabecerasSeguridad:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        ruta = scope["path"]

        async def send_con_cabeceras(mensaje):
            if mensaje["type"] == "http.response.start":
                extras = [(b"x-content-type-options", b"nosniff"),
                          (b"x-frame-options", b"DENY"),
                          (b"referrer-policy", b"no-referrer")]
                if not ruta.startswith(SIN_CSP):
                    extras.append((b"content-security-policy", CSP))
                if ruta.startswith("/api/"):
                    extras.append((b"cache-control", b"no-store"))
                mensaje = {**mensaje, "headers": list(mensaje.get("headers", [])) + extras}
            await send(mensaje)

        await self.app(scope, receive, send_con_cabeceras)
