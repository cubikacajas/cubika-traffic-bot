import os
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="CUBIKA TRAFFIC BOT")


TIENDANUBE_CLIENT_ID = os.getenv("TIENDANUBE_CLIENT_ID", "")
TIENDANUBE_CLIENT_SECRET = os.getenv("TIENDANUBE_CLIENT_SECRET", "")
TIENDANUBE_REDIRECT_URI = os.getenv("TIENDANUBE_REDIRECT_URI", "")


@app.get("/")
async def home():
    return {
        "status": "ok",
        "app": "CUBIKA TRAFFIC BOT",
        "message": "Backend funcionando correctamente."
    }


@app.get("/install")
async def install():
    if not TIENDANUBE_CLIENT_ID or not TIENDANUBE_REDIRECT_URI:
        return JSONResponse(
            {"error": "Faltan variables de Tiendanube"},
            status_code=500
        )

    params = {
        "client_id": TIENDANUBE_CLIENT_ID,
        "redirect_uri": TIENDANUBE_REDIRECT_URI,
        "response_type": "code",
    }

    url = (
        "https://www.tiendanube.com/apps/"
        + TIENDANUBE_CLIENT_ID
        + "/authorize?"
        + urlencode(params)
    )

    return {"authorization_url": url}


@app.get("/oauth/callback", response_class=HTMLResponse)
async def oauth_callback(request: Request):
    code = request.query_params.get("code")

    if not code:
        return HTMLResponse(
            "<h2>CUBIKA TRAFFIC BOT</h2>"
            "<p>No se recibió el código de autorización.</p>",
            status_code=400
        )

    return HTMLResponse(
        "<h2>CUBIKA TRAFFIC BOT</h2>"
        "<p>Autorización recibida correctamente.</p>"
        "<p>La conexión con Tiendanube está funcionando.</p>"
    )


@app.post("/webhooks/tiendanube")
async def webhook(request: Request):
    body = await request.body()

    return {
        "received": True,
        "bytes": len(body)
    }


@app.get("/privacy", response_class=HTMLResponse)
async def privacy():
    return HTMLResponse(
        "<h2>Privacidad - CUBIKA TRAFFIC BOT</h2>"
        "<p>La aplicación utiliza únicamente los datos necesarios "
        "para operar la integración autorizada.</p>"
    )


@app.get("/terms", response_class=HTMLResponse)
async def terms():
    return HTMLResponse(
        "<h2>Términos - CUBIKA TRAFFIC BOT</h2>"
        "<p>La aplicación se utiliza para integrar y medir "
        "actividades de marketing autorizadas.</p>"
    )
