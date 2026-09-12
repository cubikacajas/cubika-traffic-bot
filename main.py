import os
from urllib.parse import urlencode
from urllib.request import Request as URLRequest, urlopen
from urllib.parse import parse_qs

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

    if not TIENDANUBE_CLIENT_ID or not TIENDANUBE_CLIENT_SECRET:
        return HTMLResponse(
            "<h2>CUBIKA TRAFFIC BOT</h2>"
            "<p>Faltan las credenciales de Tiendanube.</p>",
            status_code=500
        )

    try:
        data = urlencode({
            "client_id": TIENDANUBE_CLIENT_ID,
            "client_secret": TIENDANUBE_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
        }).encode("utf-8")

        token_request = URLRequest(
            "https://www.tiendanube.com/apps/authorize/token",
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            },
            method="POST",
        )

        with urlopen(token_request, timeout=20) as response:
            token_data = response.read().decode("utf-8")

        return HTMLResponse(
            "<h2>CUBIKA TRAFFIC BOT</h2>"
            "<p>Autorización recibida correctamente.</p>"
            "<p>La conexión con Tiendanube está funcionando.</p>"
            "<p>Token recibido correctamente.</p>"
        )

    except Exception as error:
        return HTMLResponse(
            "<h2>CUBIKA TRAFFIC BOT</h2>"
            "<p>Se recibió el código, pero hubo un error al solicitar el token.</p>"
            f"<p>Error: {str(error)}</p>",
            status_code=500
        )


@app.post("/webhooks/tiendanube")
async def webhook(request: Request):
    body = await request.body()

    return {
        "received": True,
        "bytes": len(body)
    }


@app.post("/webhooks/store-redact")
async def store_redact(request: Request):
    body = await request.json()

    print("STORE REDACT:", body)

    return {"received": True}


@app.post("/webhooks/customers-redact")
async def customers_redact(request: Request):
    body = await request.json()

    print("CUSTOMERS REDACT:", body)

    return {"received": True}


@app.post("/webhooks/customers-data-request")
async def customers_data_request(request: Request):
    body = await request.json()

    print("CUSTOMERS DATA REQUEST:", body)

    return {"received": True}


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
