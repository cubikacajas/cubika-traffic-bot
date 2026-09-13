import os
import json
import html
from urllib.parse import urlencode
from urllib.request import Request as URLRequest, urlopen

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="CUBIKA TRAFFIC BOT")


TIENDANUBE_CLIENT_ID = os.getenv("TIENDANUBE_CLIENT_ID", "")
TIENDANUBE_CLIENT_SECRET = os.getenv("TIENDANUBE_CLIENT_SECRET", "")
TIENDANUBE_REDIRECT_URI = os.getenv("TIENDANUBE_REDIRECT_URI", "")
TIENDANUBE_ACCESS_TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN", "")
TIENDANUBE_STORE_ID = os.getenv("TIENDANUBE_STORE_ID", "")


def get_products():
    if not TIENDANUBE_ACCESS_TOKEN or not TIENDANUBE_STORE_ID:
        return []

    products_request = URLRequest(
        f"https://api.tiendanube.com/v1/{TIENDANUBE_STORE_ID}/products",
        headers={
            "Authentication": f"bearer {TIENDANUBE_ACCESS_TOKEN}",
            "User-Agent": "CUBIKA TRAFFIC BOT",
            "Content-Type": "application/json",
        },
        method="GET",
    )

    with urlopen(products_request, timeout=20) as response:
        products_data = response.read().decode("utf-8")

    return json.loads(products_data)


def get_translation(value, default=""):
    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        return (
            value.get("es")
            or value.get("pt")
            or value.get("en")
            or default
        )

    return default


def build_tracking_url(product_url, source):
    params = {
        "utm_source": source,
        "utm_medium": "social",
        "utm_campaign": "cubika_traffic_bot",
    }

    separator = "&" if "?" in product_url else "?"
    return product_url + separator + urlencode(params)


@app.get("/")
async def home():
    return {
        "status": "ok",
        "app": "CUBIKA TRAFFIC BOT",
        "message": "Backend funcionando correctamente.",
        "dashboard": "/dashboard",
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    connected = bool(
        TIENDANUBE_ACCESS_TOKEN and TIENDANUBE_STORE_ID
    )

    api_ok = False

    try:
        products = get_products() if connected else []
        api_ok = connected
    except Exception:
        products = []
        api_ok = False

    product_cards = ""

    for product in products[:30]:
        name = get_translation(
            product.get("name"),
            "Producto sin nombre"
        )

        handle = get_translation(
            product.get("handle"),
            ""
        )

        canonical_url = product.get("canonical_url", "")

        if not canonical_url and handle:
            canonical_url = (
                "https://cubikacajas.mitiendanube.com/"
                f"productos/{handle}"
            )

        variants = product.get("variants", [])
        price = "Sin precio"

        if variants:
            price_value = variants[0].get("price")

            if price_value:
                price = f"$ {price_value}"

        images = product.get("images", [])
        image_url = ""

        if images:
            image_url = images[0].get("src", "")

        safe_name = html.escape(str(name))
        safe_price = html.escape(str(price))
        safe_image = html.escape(str(image_url))
        safe_url = html.escape(str(canonical_url))

        if image_url:
            image_html = (
                f'<img src="{safe_image}" '
                f'alt="{safe_name}" class="product-image">'
            )
        else:
            image_html = (
                '<div class="no-image">Sin imagen</div>'
            )

        marketing_html = ""

        if canonical_url:
            instagram_url = build_tracking_url(
                canonical_url,
                "instagram"
            )

            facebook_url = build_tracking_url(
                canonical_url,
                "facebook"
            )

            whatsapp_url = build_tracking_url(
                canonical_url,
                "whatsapp"
            )

            instagram_url_safe = html.escape(
                instagram_url,
                quote=True
            )

            facebook_url_safe = html.escape(
                facebook_url,
                quote=True
            )

            whatsapp_url_safe = html.escape(
                whatsapp_url,
                quote=True
            )

            marketing_html = f"""
            <div class="marketing-links">

                <div class="marketing-title">
                    Enlaces de campaña
                </div>

                <button
                    class="channel-button"
                    onclick="copyLink('{instagram_url_safe}', this)"
                >
                    Copiar Instagram
                </button>

                <button
                    class="channel-button"
                    onclick="copyLink('{facebook_url_safe}', this)"
                >
                    Copiar Facebook
                </button>

                <button
                    class="channel-button"
                    onclick="copyLink('{whatsapp_url_safe}', this)"
                >
                    Copiar WhatsApp
                </button>

            </div>
            """

        product_cards += f"""
        <div class="product-card">

            {image_html}

            <div class="product-info">

                <h3>{safe_name}</h3>

                <div class="price">
                    {safe_price}
                </div>

                {
                    f'<a href="{safe_url}" '
                    f'target="_blank" '
                    f'class="product-button">'
                    f'Ver producto</a>'
                    if canonical_url
                    else ""
                }

                {marketing_html}

            </div>

        </div>
        """

    status_text = "Conectado" if connected else "Desconectado"

    status_class = (
        "connected"
        if connected
        else "disconnected"
    )

    api_text = "OK" if api_ok else "ERROR"

    html_page = f"""
    <!DOCTYPE html>

    <html lang="es">

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>CUBIKA TRAFFIC BOT</title>

        <style>

            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                font-family: Arial, Helvetica, sans-serif;
                background: #f4f6f8;
                color: #222;
            }}

            header {{
                background: #111827;
                color: white;
                padding: 24px 30px;
            }}

            header h1 {{
                margin: 0;
                font-size: 28px;
            }}

            header p {{
                margin: 6px 0 0;
                color: #d1d5db;
            }}

            .container {{
                max-width: 1250px;
                margin: 0 auto;
                padding: 30px 20px;
            }}

            .status-card {{
                background: white;
                border-radius: 14px;
                padding: 22px;
                margin-bottom: 25px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            }}

            .status-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 20px;
                flex-wrap: wrap;
            }}

            .status-badge {{
                display: inline-block;
                padding: 8px 14px;
                border-radius: 999px;
                color: white;
                font-weight: bold;
            }}

            .connected {{
                background: #16a34a;
            }}

            .disconnected {{
                background: #dc2626;
            }}

            .stats {{
                display: grid;
                grid-template-columns:
                    repeat(auto-fit, minmax(180px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }}

            .stat {{
                background: #f9fafb;
                border-radius: 10px;
                padding: 16px;
            }}

            .stat strong {{
                display: block;
                font-size: 22px;
                margin-top: 5px;
            }}

            .marketing-intro {{
                background: white;
                padding: 20px;
                border-radius: 14px;
                margin: 25px 0;
                box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            }}

            .marketing-intro h2 {{
                margin-top: 0;
            }}

            .marketing-intro p {{
                margin-bottom: 0;
                line-height: 1.5;
                color: #4b5563;
            }}

            .products-grid {{
                display: grid;
                grid-template-columns:
                    repeat(auto-fill, minmax(240px, 1fr));
                gap: 20px;
            }}

            .product-card {{
                background: white;
                border-radius: 14px;
                overflow: hidden;
                box-shadow: 0 4px 16px rgba(0,0,0,0.08);
                display: flex;
                flex-direction: column;
            }}

            .product-image {{
                width: 100%;
                height: 220px;
                object-fit: cover;
                background: #eee;
            }}

            .no-image {{
                height: 220px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #e5e7eb;
                color: #6b7280;
            }}

            .product-info {{
                padding: 16px;
                display: flex;
                flex-direction: column;
                flex-grow: 1;
            }}

            .product-info h3 {{
                font-size: 16px;
                margin: 0 0 12px;
                line-height: 1.35;
            }}

            .price {{
                font-size: 19px;
                font-weight: bold;
                margin-bottom: 14px;
            }}

            .product-button {{
                display: block;
                background: #111827;
                color: white;
                text-decoration: none;
                padding: 10px 14px;
                border-radius: 8px;
                text-align: center;
                margin-bottom: 14px;
            }}

            .marketing-links {{
                border-top: 1px solid #e5e7eb;
                padding-top: 14px;
                margin-top: auto;
            }}

            .marketing-title {{
                font-size: 13px;
                font-weight: bold;
                margin-bottom: 9px;
                color: #374151;
            }}

            .channel-button {{
                width: 100%;
                border: 1px solid #d1d5db;
                background: white;
                padding: 9px;
                margin-bottom: 7px;
                border-radius: 7px;
                cursor: pointer;
                font-weight: 600;
            }}

            .channel-button:hover {{
                background: #f3f4f6;
            }}

            .empty {{
                background: white;
                padding: 25px;
                border-radius: 12px;
            }}

            footer {{
                text-align: center;
                padding: 30px;
                color: #6b7280;
                font-size: 14px;
            }}

        </style>

    </head>

    <body>

        <header>

            <h1>CUBIKA TRAFFIC BOT</h1>

            <p>
                Marketing y tráfico para CUBIKACAJAS
            </p>

        </header>

        <div class="container">

            <div class="status-card">

                <div class="status-row">

                    <div>

                        <h2 style="margin:0;">
                            Estado de conexión
                        </h2>

                        <p>
                            Tienda ID:
                            {html.escape(TIENDANUBE_STORE_ID or "No configurada")}
                        </p>

                    </div>

                    <span class="status-badge {status_class}">
                        {status_text}
                    </span>

                </div>

                <div class="stats">

                    <div class="stat">
                        Productos cargados
                        <strong>{len(products)}</strong>
                    </div>

                    <div class="stat">
                        Estado API
                        <strong>{api_text}</strong>
                    </div>

                    <div class="stat">
                        Permiso
                        <strong>Solo lectura</strong>
                    </div>

                </div>

            </div>

            <div class="marketing-intro">

                <h2>
                    Marketing y Tráfico
                </h2>

                <p>
                    Cada botón genera un enlace especial para
                    Instagram, Facebook o WhatsApp.
                    Las visitas que lleguen mediante esos enlaces
                    podrán diferenciarse por canal mediante UTM.
                </p>

            </div>

            <h2>
                Productos de CUBIKACAJAS
            </h2>

            {
                f'<div class="products-grid">'
                f'{product_cards}'
                f'</div>'
                if product_cards
                else
                '<div class="empty">'
                'No se encontraron productos.'
                '</div>'
            }

        </div>

        <footer>
            CUBIKA TRAFFIC BOT
        </footer>

        <script>

            async function copyLink(url, button) {{

                const originalText = button.innerText;

                try {{

                    await navigator.clipboard.writeText(url);

                    button.innerText = "Copiado ✓";

                    setTimeout(function() {{
                        button.innerText = originalText;
                    }}, 1500);

                }} catch (error) {{

                    window.prompt(
                        "Copiá este enlace:",
                        url
                    );

                }}

            }}

        </script>

    </body>

    </html>
    """

    return HTMLResponse(html_page)


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
                "Content-Type":
                    "application/x-www-form-urlencoded"
            },
            method="POST",
        )

        with urlopen(token_request, timeout=20) as response:
            token_response = (
                response.read().decode("utf-8")
            )

        token_data = json.loads(token_response)

        access_token = token_data.get("access_token")

        store_id = (
            token_data.get("user_id")
            or token_data.get("store_id")
        )

        if not access_token or not store_id:
            return HTMLResponse(
                "<h2>CUBIKA TRAFFIC BOT</h2>"
                "<p>Tiendanube respondió, "
                "pero faltan datos de autorización.</p>",
                status_code=500
            )

        return HTMLResponse(
            "<h2>CUBIKA TRAFFIC BOT</h2>"
            "<p>Autorización recibida correctamente.</p>"
            "<p>La conexión con Tiendanube está funcionando.</p>"
            '<p><a href="/dashboard">'
            "Abrir panel"
            "</a></p>"
        )

    except Exception as error:
        return HTMLResponse(
            "<h2>CUBIKA TRAFFIC BOT</h2>"
            "<p>Se recibió el código, pero hubo "
            "un error al solicitar el token.</p>"
            f"<p>Error: {html.escape(str(error))}</p>",
            status_code=500
        )


@app.get("/connection-status")
async def connection_status():

    return {
        "connected": bool(
            TIENDANUBE_ACCESS_TOKEN
            and TIENDANUBE_STORE_ID
        ),
        "store_id": (
            TIENDANUBE_STORE_ID
            if TIENDANUBE_STORE_ID
            else None
        ),
    }


@app.get("/products")
async def products():

    if not TIENDANUBE_ACCESS_TOKEN or not TIENDANUBE_STORE_ID:

        return JSONResponse(
            {
                "error":
                    "La conexión con Tiendanube "
                    "no está configurada."
            },
            status_code=500
        )

    try:

        products_data = get_products()

        return JSONResponse(
            content=products_data
        )

    except Exception as error:

        return JSONResponse(
            {
                "error":
                    "No se pudieron consultar los productos.",
                "detail": str(error),
            },
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

    await request.json()

    return {"received": True}


@app.post("/webhooks/customers-redact")
async def customers_redact(request: Request):

    await request.json()

    return {"received": True}


@app.post("/webhooks/customers-data-request")
async def customers_data_request(request: Request):

    await request.json()

    return {"received": True}


@app.get("/privacy", response_class=HTMLResponse)
async def privacy():

    return HTMLResponse(
        "<h2>Privacidad - CUBIKA TRAFFIC BOT</h2>"
        "<p>La aplicación utiliza únicamente los datos "
        "necesarios para operar la integración autorizada.</p>"
    )


@app.get("/terms", response_class=HTMLResponse)
async def terms():

    return HTMLResponse(
        "<h2>Términos - CUBIKA TRAFFIC BOT</h2>"
        "<p>La aplicación se utiliza para integrar y medir "
        "actividades de marketing autorizadas.</p>"
    )
