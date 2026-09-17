import os
import json
import html
from urllib.parse import urlencode, quote_plus
from urllib.request import Request as URLRequest, urlopen

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account


app = FastAPI(title="CUBIKA TRAFFIC BOT")


# ============================================================
# CONFIGURACION TIENDANUBE
# ============================================================

TIENDANUBE_CLIENT_ID = os.getenv("TIENDANUBE_CLIENT_ID", "")
TIENDANUBE_CLIENT_SECRET = os.getenv("TIENDANUBE_CLIENT_SECRET", "")
TIENDANUBE_REDIRECT_URI = os.getenv("TIENDANUBE_REDIRECT_URI", "")
TIENDANUBE_ACCESS_TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN", "")
TIENDANUBE_STORE_ID = os.getenv("TIENDANUBE_STORE_ID", "")


# ============================================================
# CONFIGURACION GOOGLE ANALYTICS 4
# ============================================================

GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID", "")

GA4_CREDENTIALS_FILE = "/etc/secrets/ga4-service-account.json"


# ============================================================
# TIENDANUBE
# ============================================================

def get_products():
    if not TIENDANUBE_ACCESS_TOKEN or not TIENDANUBE_STORE_ID:
        return []

    all_products = []
    page = 1
    per_page = 30

    while True:
        request = URLRequest(
            f"https://api.tiendanube.com/v1/{TIENDANUBE_STORE_ID}/products?page={page}&per_page={per_page}",
            headers={
                "Authentication": f"bearer {TIENDANUBE_ACCESS_TOKEN}",
                "User-Agent": "CUBIKA TRAFFIC BOT",
                "Content-Type": "application/json",
            },
            method="GET",
        )

        with urlopen(request, timeout=20) as response:
            data = response.read().decode("utf-8")

        products = json.loads(data)

        if not products:
            break

        all_products.extend(products)

        if len(products) < per_page:
            break

        page += 1

    return all_products

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


def build_tracking_url(product_url, source, product_name=""):

    params = {
        "utm_source": source,
        "utm_medium": "social",
        "utm_campaign": "cubika_traffic_bot",
        "utm_content": product_name,
    }

    separator = "&" if "?" in product_url else "?"

    return product_url + separator + urlencode(params)


# ============================================================
# GOOGLE ANALYTICS 4
# ============================================================

def get_ga4_client():

    if not os.path.exists(GA4_CREDENTIALS_FILE):
        raise FileNotFoundError(
            "No se encontró el archivo secreto de GA4."
        )

    credentials = (
        service_account.Credentials.from_service_account_file(
            GA4_CREDENTIALS_FILE
        )
    )

    return BetaAnalyticsDataClient(
        credentials=credentials
    )


def get_ga4_summary():

    if not GA4_PROPERTY_ID:
        raise ValueError(
            "GA4_PROPERTY_ID no está configurado."
        )

    client = get_ga4_client()

    request = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[
            DateRange(
                start_date="30daysAgo",
                end_date="today",
            )
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
            Metric(name="screenPageViews"),
        ],
    )

    response = client.run_report(request)

    result = {
        "sessions": 0,
        "active_users": 0,
        "views": 0,
    }

    if response.rows:

        values = response.rows[0].metric_values

        result["sessions"] = int(float(values[0].value or 0))
        result["active_users"] = int(float(values[1].value or 0))
        result["views"] = int(float(values[2].value or 0))

    return result


def get_ga4_traffic_sources():

    if not GA4_PROPERTY_ID:
        raise ValueError(
            "GA4_PROPERTY_ID no está configurado."
        )

    client = get_ga4_client()

    request = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[
            DateRange(
                start_date="30daysAgo",
                end_date="today",
            )
        ],
       dimensions=[
    Dimension(name="sessionManualSource"),
    Dimension(name="sessionManualMedium"),
    Dimension(name="sessionManualCampaignName"),
    Dimension(name="sessionManualAdContent"),
],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
        ],
        limit=100,
    )

    response = client.run_report(request)

    sources = []

    for row in response.rows:

        sources.append({
            "source": row.dimension_values[0].value,
            "medium": row.dimension_values[1].value,
            "campaign": row.dimension_values[2].value,
            "content": row.dimension_values[3].value,
            "sessions": int(
                float(row.metric_values[0].value or 0)
            ),
            "users": int(
                float(row.metric_values[1].value or 0)
            ),
        })

    return sources
# ==================================================
# GOOGLE SEARCH CONSOLE
# ==================================================

def get_search_console_status():
    """
    Punto de preparación para integrar Google Search Console.
    Más adelante devolverá consultas, clics, impresiones,
    CTR y posición media de CUBIKACAJAS.
    """
    return {
        "connected": False,
        "status": "pending",
        "message": "Google Search Console pendiente de conexión."
    }


# ====================================================
# OPORTUNIDADES DE BUSQUEDA EN GOOGLE
# ====================================================

def generate_seo_suggestion(product_name, search_opportunities):
    """
    Genera un título y una descripción SEO sugeridos.
    No modifica el producto en Tiendanube.
    """

    name = (product_name or "").strip()

    if not name:
        return {
            "title": "",
            "description": ""
        }

    if search_opportunities:
        main_keyword = search_opportunities[0]
    else:
        main_keyword = name

    seo_title = f"{main_keyword.title()} | CUBIKACAJAS"

    seo_description = (
        f"Encontrá {main_keyword} en CUBIKACAJAS. "
        f"Packaging de cartulina para emprendimientos, comercios, "
        f"pastelerías y regalos. Conocé nuestros modelos y opciones."
    )

    return {
        "title": seo_title,
        "description": seo_description
    }


def generate_search_opportunities(product_name):
    """
    Genera oportunidades de búsqueda según la familia
    del producto de Tiendanube.
    """

    name = (product_name or "").strip()

    if not name:
        return []

    name_lower = name.lower()
    opportunities = []

    search_groups = [
        {
            "keywords": ["bombon"],
            "searches": [
                "cajas para bombones",
                "cajas para chocolates",
                "packaging para bombones",
                "cajas para regalar bombones",
                "cajas para emprendimientos de chocolates",
                              ],
        }, {
            "keywords": ["valija"],
            "searches": [
                "cajas valija",
                "cajas tipo valija",
                "cajas valija con visor",
                "cajas de cartulina tipo valija",
                "packaging tipo valija",
            ],
        },
        {
            "keywords": ["cajita feliz"],
            "searches": [
                "cajitas para regalos",
                "cajitas de cartulina",
                "cajas para souvenirs",
                "cajitas para cumpleaños",
                "packaging para regalos",
            ],
        },
        {
            "keywords": ["base kraft", "bases kraft"],
            "searches": [
                "bases de cartón kraft",
                "bases kraft para pastelería",
                "bases para tortas",
                "bases de cartón para repostería",
                "bases kraft para alimentos",
            ],
        },
        {
            "keywords": ["caja mesa"],
            "searches": [
                "cajas para mesa dulce",
                "cajas para candy bar",
                "cajas de cartulina para mesa dulce",
                "packaging para mesa dulce",
                "cajas para eventos",
            ],
        },
        {
            "keywords": ["tags"],
            "searches": [
                "tags para regalos",
                "etiquetas para regalos",
                "tags de cartulina",
                "etiquetas para packaging",
                "tags para emprendimientos",
            ],
        },
        {
            "keywords": ["línea selección", "linea seleccion"],
            "searches": [
                "cajas de cartulina premium",
                "cajas premium para regalos",
                "packaging premium",
                "cajas para emprendimientos",
                "cajas de presentación",
            ],
        },
       
        {
            "keywords": ["torta", "minitorta", "mini torta"],
            "searches": [
                "cajas para tortas",
                "cajas de cartulina para tortas",
                "packaging para tortas",
                "cajas para pastelería",
                "cajas para transportar tortas",
            ],
        },
        {
            "keywords": ["cupcake", "muffin"],
            "searches": [
                "cajas para cupcakes",
                "cajas para muffins",
                "packaging para cupcakes",
                "cajas para cupcakes con visor",
                "cajas para pastelería",
            ],
        },
        {
            "keywords": ["alfajor"],
            "searches": [
                "cajas para alfajores",
                "packaging para alfajores",
                "cajas de cartulina para alfajores",
                "cajas para vender alfajores",
                "cajas para emprendimientos de alfajores",
            ],
        },
        {
            "keywords": ["cookie", "gallet"],
            "searches": [
                "cajas para cookies",
                "cajas para galletitas",
                "packaging para cookies",
                "cajas para cookies con visor",
                "cajas para emprendimientos de galletitas",
            ],
        },
        {
            "keywords": ["macaron"],
            "searches": [
                "cajas para macarons",
                "packaging para macarons",
                "cajas de cartulina para macarons",
                "cajas para regalar macarons",
            ],
        },
        {
            "keywords": ["budín", "budin"],
            "searches": [
                "cajas para budines",
                "packaging para budines",
                "cajas de cartulina para budines",
                "cajas para budín artesanal",
            ],
        },
        {
            "keywords": ["desayuno"],
            "searches": [
                "cajas para desayunos",
                "cajas para desayunos sorpresa",
                "packaging para desayunos",
                "cajas para desayunos de regalo",
            ],
        },
        {
            "keywords": ["multiuso"],
            "searches": [
                "cajas multiuso",
                "cajas de cartulina multiuso",
                "cajas multiuso con visor",
                "cajas para emprendimientos",
                "packaging multiuso",
            ],
        },
        {
            "keywords": ["vino"],
            "searches": [
                "cajas para botellas de vino",
                "estuches para vino",
                "cajas de cartulina para vino",
                "packaging para botellas de vino",
            ],
        },
        {
            "keywords": ["pochoc"],
            "searches": [
                "cajas para pochoclos",
                "pochocleras de cartulina",
                "envases para pochoclos",
                "pochocleras para cumpleaños",
            ],
        },
        {
            "keywords": ["porta flores", "portaflores"],
            "searches": [
                "cajas porta flores",
                "envases para flores",
                "packaging para flores",
                "cajas de cartulina para flores",
            ],
        },
        {
            "keywords": ["canasta"],
            "searches": [
                "canastas de cartulina",
                "cajas tipo canasta",
                "canastas para regalos",
                "packaging tipo canasta",
            ],
        },
        {
            "keywords": ["caja sobre"],
            "searches": [
                "cajas tipo sobre",
                "cajas sobre para regalos",
                "packaging tipo sobre",
                "sobres de cartulina para regalos",
            ],
        },
        {
            "keywords": ["día del niño", "dia del niño"],
            "searches": [
                "cajas para día del niño",
                "packaging día del niño",
                "cajas de regalo día del niño",
                "cajas para regalos infantiles",
            ],
        },
        {
            "keywords": ["papá", "papa"],
            "searches": [
                "cajas para día del padre",
                "cajas de regalo para papá",
                "packaging día del padre",
                "cajas para regalos día del padre",
            ],
        },
        {
            "keywords": ["madre"],
            "searches": [
                "cajas para día de la madre",
                "cajas de regalo para mamá",
                "packaging día de la madre",
                "cajas para regalos día de la madre",
            ],
        },
        {
            "keywords": ["pascua"],
            "searches": [
                "cajas para pascuas",
                "cajas para huevos de pascua",
                "packaging para pascuas",
                "cajas de regalo para pascuas",
            ],
        },
        {
            "keywords": ["navide", "navidad", "felices fiestas"],
            "searches": [
                "cajas navideñas",
                "cajas para regalos de navidad",
                "packaging navideño",
                "cajas de cartulina para navidad",
            ],
        },
        {
            "keywords": ["adviento"],
            "searches": [
                "cajas de adviento",
                "cajas calendario de adviento",
                "packaging calendario de adviento",
                "cajas para calendario de navidad",
            ],
        },
        {
           "keywords": ["amor", "línea amor", "linea amor"],
            "searches": [
                "cajas para regalos románticos",
                "cajas con corazones",
                "packaging para san valentín",
                "cajas para día de los enamorados",
            ],
        },
        {
            "keywords": ["apilable", "delicia", "dulces momentos"],
            "searches": [
                "cajas para productos de pastelería",
                "cajas para dulces",
                "packaging para repostería",
                "cajas de cartulina para emprendimientos",
            ],
        },
        {
            "keywords": ["regalo", "princess"],
            "searches": [
                "cajas para regalos",
                "cajas de cartulina para regalos",
                "packaging para regalos",
                "cajas para emprendimientos",
            ],
        },
    ]

    for group in search_groups:
        if any(keyword in name_lower for keyword in group["keywords"]):
            opportunities.extend(group["searches"])

    return list(dict.fromkeys(opportunities))
    
@app.get("/search-opportunities-test")
async def search_opportunities_test():
    products = get_products()

    results = []
    products_without_opportunities = []

    for product in products:
        product_name = get_translation(product.get("name"), "")

        opportunities = generate_search_opportunities(product_name)

        if opportunities:
            results.append({
                "id": product.get("id"),
                "product": product_name,
                "search_opportunities": opportunities,
            })
        else:
            products_without_opportunities.append({
                "id": product.get("id"),
                "product": product_name,
            })

    return {
        "total_products": len(products),
        "products_with_opportunities": len(results),
        "products_without_opportunities_count": len(products_without_opportunities),
        "results": results,
        "products_without_opportunities": products_without_opportunities,
    }
# ============================================================
# CLASIFICACION DE TRAFICO
# ============================================================

def detect_channel(source):

    source = (source or "").strip().lower()

    # Instagram
    if (
        source in {"instagram", "ig"}
        or "instagram.com" in source
    ):
        return "instagram"

    # Facebook
    if (
        source in {"facebook", "fb"}
        or "facebook.com" in source
    ):
        return "facebook"

    # WhatsApp
    if (
        source in {"whatsapp", "wa"}
        or "whatsapp.com" in source
        or "wa.me" in source
    ):
        return "whatsapp"

    return None


def summarize_channels(sources):

    result = {
        # Trafico social real
        "instagram_total": 0,
        "facebook_total": 0,
        "whatsapp_total": 0,

        # Trafico identificado por CUBIKA TRAFFIC BOT
        "campaign_total": 0,
        "campaign_instagram": 0,
        "campaign_facebook": 0,
        "campaign_whatsapp": 0,
    }

    for row in sources:

        source = row.get("source", "")
        campaign = (
            row.get("campaign", "")
            .strip()
            .lower()
        )

        sessions = row.get("sessions", 0)

        channel = detect_channel(source)

        # Trafico real por red
        if channel == "instagram":
            result["instagram_total"] += sessions

        elif channel == "facebook":
            result["facebook_total"] += sessions

        elif channel == "whatsapp":
            result["whatsapp_total"] += sessions

        # Trafico generado por nuestros enlaces UTM
        if campaign == "cubika_traffic_bot":

            result["campaign_total"] += sessions

            if channel == "instagram":
                result["campaign_instagram"] += sessions

            elif channel == "facebook":
                result["campaign_facebook"] += sessions

            elif channel == "whatsapp":
                result["campaign_whatsapp"] += sessions

    return result


# ============================================================
# INICIO
# ============================================================

@app.get("/")
async def home():

    return {
        "status": "ok",
        "app": "CUBIKA TRAFFIC BOT",
        "message": "Backend funcionando correctamente.",
        "dashboard": "/dashboard",
    }


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():

    # --------------------------------------------------------
    # TIENDANUBE
    # --------------------------------------------------------

    connected = bool(
        TIENDANUBE_ACCESS_TOKEN
        and TIENDANUBE_STORE_ID
    )

    api_ok = False

    try:

        products = get_products() if connected else []
        api_ok = connected

    except Exception:

        products = []
        api_ok = False


    # --------------------------------------------------------
    # GA4
    # --------------------------------------------------------

    ga4_ok = False
    ga4_error = ""

    ga4_summary = {
        "sessions": 0,
        "active_users": 0,
        "views": 0,
    }

    ga4_sources = []

    channels = {
        "instagram_total": 0,
        "facebook_total": 0,
        "whatsapp_total": 0,
        "campaign_total": 0,
        "campaign_instagram": 0,
        "campaign_facebook": 0,
        "campaign_whatsapp": 0,
    }

    try:

        ga4_summary = get_ga4_summary()
        ga4_sources = get_ga4_traffic_sources()
        channels = summarize_channels(ga4_sources)

        ga4_ok = True

    except Exception as error:

        ga4_error = str(error)
        ga4_ok = False


    # --------------------------------------------------------
    # PRODUCTOS
    # --------------------------------------------------------

    product_cards = ""

    for product in products:

        name = get_translation(
            product.get("name"),
            "Producto sin nombre"
        )

        handle = get_translation(
            product.get("handle"),
            ""
        )

        canonical_url = product.get(
            "canonical_url",
            ""
        )

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

        safe_image = html.escape(
            str(image_url),
            quote=True
        )

        safe_url = html.escape(
            str(canonical_url),
            quote=True
        )

        if image_url:

            image_html = (
                f'<img src="{safe_image}" '
                f'alt="{safe_name}" '
                f'class="product-image">'
            )

        else:

            image_html = (
                '<div class="no-image">'
                'Sin imagen'
                '</div>'
            )
        search_opportunities = generate_search_opportunities(name)
        seo_suggestion = generate_seo_suggestion(name, search_opportunities)
seo_html = f"""
<div class="seo-suggestion">
    <h4>🚀 Sugerencia SEO</h4>
    <p><strong>Título SEO sugerido:</strong><br>
    {html.escape(seo_suggestion["title"])}</p>

    <p><strong>Descripción SEO sugerida:</strong><br>
    {html.escape(seo_suggestion["description"])}</p>
</div>
"""
opportunities_html = ""

if search_opportunities:
            opportunities_items = "".join(
                f'<li>{html.escape(opportunity)} '
                f'<a href="https://www.google.com/search?q={quote_plus(opportunity)}" '
                f'target="_blank">Buscar en Google</a></li>'
                for opportunity in search_opportunities
            )

            opportunities_html = f"""
            <div class="search-opportunities">
                <h4>🔎 Oportunidades de búsqueda en Google</h4>
                <ul>
                    {opportunities_items}
                </ul>
            </div>
            """
            

marketing_html = ""

        if canonical_url:

                    
            instagram_url = build_tracking_url(
                canonical_url,
                "instagram",
                name
            )

            facebook_url = build_tracking_url(
                canonical_url,
                "facebook",
                name
            )

            whatsapp_url = build_tracking_url(
                canonical_url,
                "whatsapp",
                name
            )

            instagram_safe = html.escape(
                instagram_url,
                quote=True
            )

            instagram_safe = html.escape(
                instagram_url,
                quote=True
            )

            facebook_safe = html.escape(
                facebook_url,
                quote=True
            )

            whatsapp_safe = html.escape(
                whatsapp_url,
                quote=True
            )

            instagram_text = (
                f"🎁 {name}\n\n"
                "Packaging CUBIKACAJAS para darle una presentación "
                "especial a tus productos.\n\n"
                f"📦 Presentación: {name}\n"
                f"💰 Precio: {price}\n\n"
                "✨ Ideal para emprendimientos, pastelerías, "
                "comercios y regalos.\n\n"
                "👉 Mirá el producto acá:\n"
                f"{instagram_url}\n\n"
                "#CUBIKACAJAS #Packaging #Cajas "
                "#Emprendedores #Pasteleria"
            )

            instagram_text_safe = html.escape(
                instagram_text,
                quote=True
            ).replace("\n", "&#10;")
            facebook_text = (
                f"📦 {name}\n\n"
                "Packaging CUBIKACAJAS para presentar tus productos "
                "con calidad y estilo.\n\n"
                f"💰 Precio: {price}\n\n"
                "✨ Ideal para pastelerías, emprendimientos, "
                "comercios y regalos.\n\n"
                "👉 Conocé el producto y comprá online:\n"
                f"{facebook_url}\n\n"
                "#CUBIKACAJAS #Packaging #Cajas "
                "#Pasteleria #Emprendedores"
            )

            facebook_text_safe = html.escape(
                facebook_text,
                quote=True
            ).replace("\n", "&#10;")
            whatsapp_text = (
                f"📦 {name}\n\n"
                "Packaging CUBIKACAJAS ✨\n\n"
                f"💰 Precio: {price}\n\n"
                "Ideal para pastelerías, emprendimientos, "
                "comercios y regalos.\n\n"
                "👉 Mirá el producto y comprá online:\n"
                f"{whatsapp_url}"
            )

            whatsapp_text_safe = html.escape(
                whatsapp_text,
                quote=True
            ).replace("\n", "&#10;")
            marketing_html = f"""
            <div class="marketing-links">

                <div class="marketing-title">
                    Enlaces de campaña CUBIKA
                </div>

                <button
                    class="channel-button"
                    onclick="copyLink(
                        '{instagram_safe}',
                        this
                    )"
                >
                    Copiar Instagram
                </button>

                                <button
                    class="channel-button"
                    data-text="{instagram_text_safe}"
                    onclick="copyLink(
                        this.dataset.text,
                        this
                    )"
                >
                    Copiar texto Instagram
                </button>

                <button
                    class="channel-button"
                    onclick="copyLink(
                        '{facebook_safe}',
                        this
                    )"
                >
                    Copiar Facebook
                </button>

                               <button
                    class="channel-button"
                    data-text="{facebook_text_safe}"
                    onclick="copyLink(
                        this.dataset.text,
                        this
                    )"
                >
                                     Copiar texto Facebook
                </button>

                <button
                    class="channel-button"
                    onclick="copyLink(
                        '{whatsapp_safe}',
                        this
                    )"
                >
                    Copiar WhatsApp
                </button>
                <button
                    class="channel-button"
                    data-text="{whatsapp_text_safe}"
                    onclick="copyLink(
                        this.dataset.text,
                        this
                    )"
                >
                    Copiar texto WhatsApp
                </button>
            </div>
            """

        product_cards += f"""
        <div class="product-card">

            {image_html}

            <div class="product-info">

                <h3>
                    {safe_name}
                </h3>

                <div class="price">
                    {safe_price}
                </div>

                {
                    f'<a href="{safe_url}" '
                    f'target="_blank" '
                    f'class="product-button">'
                    f'Ver producto'
                    f'</a>'
                    if canonical_url
                    else ""
                }

            {marketing_html}
            {opportunities_html}
            {seo_html}

            </div>

        </div>
        """


    # --------------------------------------------------------
    # TABLA GA4
    # --------------------------------------------------------

    traffic_rows = ""

    for row in ga4_sources:

        source = html.escape(
            row.get("source", "") or "(direct)"
        )

        medium = html.escape(
            row.get("medium", "") or "-"
        )

        campaign = html.escape(
            row.get("campaign", "") or "-"
        )
        content = html.escape(
            row.get("content", "") or "-"
        )
        sessions = row.get("sessions", 0)
        users = row.get("users", 0)

        channel = detect_channel(
            row.get("source", "")
        )

        channel_label = {
            "instagram": "Instagram",
            "facebook": "Facebook",
            "whatsapp": "WhatsApp",
        }.get(channel, "-")

        traffic_rows += f"""
        <tr>
            <td>{source}</td>
            <td>{medium}</td>
            <td>{campaign}</td>
            <td>{content}</td>
            <td>{channel_label}</td>
            <td>{sessions}</td>
            <td>{users}</td>
        </tr>
        """

    if not traffic_rows:

        traffic_rows = """
        <tr>
            <td colspan="6">
                No hay tráfico disponible.
            </td>
        </tr>
        """


    # --------------------------------------------------------
    # ESTADOS
    # --------------------------------------------------------

    status_text = (
        "Conectado"
        if connected
        else "Desconectado"
    )

    status_class = (
        "connected"
        if connected
        else "disconnected"
    )

    api_text = (
        "OK"
        if api_ok
        else "ERROR"
    )

    ga4_status_text = (
        "Conectado"
        if ga4_ok
        else "Error"
    )

    ga4_status_class = (
        "connected"
        if ga4_ok
        else "disconnected"
    )


    # ========================================================
    # HTML
    # ========================================================

    html_page = f"""
    <!DOCTYPE html>

    <html lang="es">

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>
            CUBIKA TRAFFIC BOT
        </title>

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

            .card {{
                background: white;
                border-radius: 14px;
                padding: 22px;
                margin-bottom: 25px;

                box-shadow:
                    0 4px 16px
                    rgba(0,0,0,0.08);
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
                    repeat(
                        auto-fit,
                        minmax(170px, 1fr)
                    );

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
                font-size: 25px;
                margin-top: 5px;
            }}

            .ga4-card {{
                border-left:
                    5px solid #f9ab00;
            }}

            .section-title {{
                margin-top: 30px;
            }}

            .channel-grid {{
                display: grid;

                grid-template-columns:
                    repeat(
                        auto-fit,
                        minmax(180px, 1fr)
                    );

                gap: 15px;
                margin-top: 15px;
            }}

            .channel-stat {{
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 18px;
            }}

            .channel-stat span {{
                display: block;
                color: #6b7280;
                font-size: 14px;
            }}

            .channel-stat strong {{
                display: block;
                font-size: 28px;
                margin-top: 7px;
            }}

            .campaign-box {{
                background: #eff6ff;
                border-radius: 12px;
                padding: 20px;
                margin-top: 25px;
            }}

            .campaign-box h3 {{
                margin-top: 0;
            }}

            .table-container {{
                overflow-x: auto;
                margin-top: 20px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
            }}

            th {{
                text-align: left;
                background: #f3f4f6;
            }}

            th,
            td {{
                padding: 12px;
                border-bottom: 1px solid #e5e7eb;
                font-size: 14px;
            }}

            .error-box {{
                margin-top: 15px;
                padding: 12px;
                background: #fef2f2;
                border-radius: 8px;
                color: #991b1b;
            }}

            .products-grid {{
                display: grid;

                grid-template-columns:
                    repeat(
                        auto-fill,
                        minmax(240px, 1fr)
                    );

                gap: 20px;
            }}

            .product-card {{
                background: white;
                border-radius: 14px;
                overflow: hidden;

                box-shadow:
                    0 4px 16px
                    rgba(0,0,0,0.08);

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

            <h1>
                CUBIKA TRAFFIC BOT
            </h1>

            <p>
                Marketing, tráfico y productos para CUBIKACAJAS
            </p>

        </header>


        <div class="container">


            <!-- TIENDANUBE -->

            <div class="card">

                <div class="status-row">

                    <div>

                        <h2 style="margin:0;">
                            Tiendanube
                        </h2>

                        <p>
                            Tienda ID:
                            {html.escape(
                                TIENDANUBE_STORE_ID
                                or "No configurada"
                            )}
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


            <!-- GA4 -->

            <div class="card ga4-card">

                <div class="status-row">

                    <div>

                        <h2 style="margin:0;">
                            Google Analytics 4
                        </h2>

                        <p>
                            Tráfico de los últimos 30 días
                        </p>

                    </div>

                    <span
                        class="status-badge {ga4_status_class}"
                    >
                        {ga4_status_text}
                    </span>

                </div>


                <div class="stats">

                    <div class="stat">
                        Sesiones
                        <strong>
                            {ga4_summary["sessions"]}
                        </strong>
                    </div>

                    <div class="stat">
                        Usuarios activos
                        <strong>
                            {ga4_summary["active_users"]}
                        </strong>
                    </div>

                    <div class="stat">
                        Vistas
                        <strong>
                            {ga4_summary["views"]}
                        </strong>
                    </div>

                </div>


                <h3 class="section-title">
                    Tráfico real por red social
                </h3>

                <div class="channel-grid">

                    <div class="channel-stat">

                        <span>
                            Instagram
                        </span>

                        <strong>
                            {channels["instagram_total"]}
                        </strong>

                        sesiones

                    </div>


                    <div class="channel-stat">

                        <span>
                            Facebook
                        </span>

                        <strong>
                            {channels["facebook_total"]}
                        </strong>

                        sesiones

                    </div>


                    <div class="channel-stat">

                        <span>
                            WhatsApp
                        </span>

                        <strong>
                            {channels["whatsapp_total"]}
                        </strong>

                        sesiones

                    </div>

                </div>


                <div class="campaign-box">

                    <h3>
                        CUBIKA TRAFFIC BOT
                    </h3>

                    <p>
                        Sesiones generadas con enlaces
                        <strong>
                            utm_campaign=cubika_traffic_bot
                        </strong>
                    </p>

                    <div class="channel-grid">

                        <div class="channel-stat">

                            <span>
                                Total campaña
                            </span>

                            <strong>
                                {channels["campaign_total"]}
                            </strong>

                        </div>


                        <div class="channel-stat">

                            <span>
                                Instagram CUBIKA
                            </span>

                            <strong>
                                {channels["campaign_instagram"]}
                            </strong>

                        </div>


                        <div class="channel-stat">

                            <span>
                                Facebook CUBIKA
                            </span>

                            <strong>
                                {channels["campaign_facebook"]}
                            </strong>

                        </div>


                        <div class="channel-stat">

                            <span>
                                WhatsApp CUBIKA
                            </span>

                            <strong>
                                {channels["campaign_whatsapp"]}
                            </strong>

                        </div>

                    </div>

                </div>


                {
                    (
                        f'<div class="error-box">'
                        f'Error GA4: '
                        f'{html.escape(ga4_error)}'
                        f'</div>'
                    )
                    if not ga4_ok
                    else ""
                }


                <h3 class="section-title">
                    Fuentes y campañas
                </h3>

                <div class="table-container">

                    <table>

                        <thead>

                            <tr>

                                <th>Fuente</th>
                                <th>Medio</th>
                                <th>Campaña</th>
                                <th>Producto</th>
                                <th>Canal reconocido</th>
                                <th>Sesiones</th>
                                <th>Usuarios</th>

                            </tr>

                        </thead>

                        <tbody>
                            {traffic_rows}
                        </tbody>

                    </table>

                </div>

            </div>


            <!-- PRODUCTOS -->

            <h2>
                Productos de CUBIKACAJAS
            </h2>


            {
                f'<div class="products-grid">'
                f'{product_cards}'
                f'</div>'
                if product_cards
                else
                '<div class="card">'
                'No se encontraron productos.'
                '</div>'
            }

        </div>


        <footer>
            CUBIKA TRAFFIC BOT
        </footer>


        <script>

            async function copyLink(url, button) {{

                const originalText =
                    button.innerText;

                try {{

                    await navigator.clipboard
                        .writeText(url);

                    button.innerText =
                        "Copiado ✓";

                    setTimeout(
                        function() {{
                            button.innerText =
                                originalText;
                        }},
                        1500
                    );

                }}

                catch (error) {{

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


# ============================================================
# ESTADO GA4
# ============================================================

@app.get("/ga4-status")
async def ga4_status():

    try:

        summary = get_ga4_summary()
        sources = get_ga4_traffic_sources()
        channels = summarize_channels(sources)

        return {
            "connected": True,
            "property_id": GA4_PROPERTY_ID,
            "data": summary,
            "channels": channels,
        }

    except Exception as error:

        return JSONResponse(
            {
                "connected": False,
                "property_id":
                    GA4_PROPERTY_ID or None,
                "error":
                    str(error),
            },
            status_code=500
        )


# ============================================================
# INSTALACION TIENDANUBE
# ============================================================

@app.get("/install")
async def install():

    if (
        not TIENDANUBE_CLIENT_ID
        or not TIENDANUBE_REDIRECT_URI
    ):

        return JSONResponse(
            {
                "error":
                    "Faltan variables de Tiendanube"
            },
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

    return {
        "authorization_url": url
    }


# ============================================================
# CALLBACK OAUTH
# ============================================================

@app.get(
    "/oauth/callback",
    response_class=HTMLResponse
)
async def oauth_callback(request: Request):

    code = request.query_params.get("code")

    if not code:

        return HTMLResponse(
            "<h2>CUBIKA TRAFFIC BOT</h2>"
            "<p>No se recibió el código de autorización.</p>",
            status_code=400
        )

    if (
        not TIENDANUBE_CLIENT_ID
        or not TIENDANUBE_CLIENT_SECRET
    ):

        return HTMLResponse(
            "<h2>CUBIKA TRAFFIC BOT</h2>"
            "<p>Faltan las credenciales de Tiendanube.</p>",
            status_code=500
        )

    try:

        data = urlencode({
            "client_id":
                TIENDANUBE_CLIENT_ID,

            "client_secret":
                TIENDANUBE_CLIENT_SECRET,

            "grant_type":
                "authorization_code",

            "code":
                code,

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

        with urlopen(
            token_request,
            timeout=20
        ) as response:

            token_response = (
                response.read()
                .decode("utf-8")
            )

        token_data = json.loads(
            token_response
        )

        access_token = token_data.get(
            "access_token"
        )

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
            '<p><a href="/dashboard">Abrir panel</a></p>'
        )

    except Exception as error:

        return HTMLResponse(
            "<h2>CUBIKA TRAFFIC BOT</h2>"
            "<p>Se recibió el código, "
            "pero hubo un error al solicitar el token.</p>"
            f"<p>Error: {html.escape(str(error))}</p>",
            status_code=500
        )


# ============================================================
# ESTADO TIENDANUBE
# ============================================================

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


# ============================================================
# PRODUCTOS
# ============================================================

@app.get("/products")
async def products():

    if (
        not TIENDANUBE_ACCESS_TOKEN
        or not TIENDANUBE_STORE_ID
    ):

        return JSONResponse(
            {
                "error":
                    "La conexión con Tiendanube no está configurada."
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
                "detail":
                    str(error),
            },
            status_code=500
        )


# ============================================================
# WEBHOOKS
# ============================================================

@app.post("/webhooks/tiendanube")
async def webhook(request: Request):

    body = await request.body()

    return {
        "received": True,
        "bytes": len(body),
    }


@app.post("/webhooks/store-redact")
async def store_redact(request: Request):

    await request.json()

    return {
        "received": True
    }


@app.post("/webhooks/customers-redact")
async def customers_redact(request: Request):

    await request.json()

    return {
        "received": True
    }


@app.post("/webhooks/customers-data-request")
async def customers_data_request(request: Request):

    await request.json()

    return {
        "received": True
    }


# ============================================================
# PRIVACIDAD
# ============================================================

@app.get(
    "/privacy",
    response_class=HTMLResponse
)
async def privacy():

    return HTMLResponse(
        "<h2>Privacidad - CUBIKA TRAFFIC BOT</h2>"
        "<p>La aplicación utiliza únicamente "
        "los datos necesarios para operar "
        "la integración autorizada.</p>"
    )


# ============================================================
# TERMINOS
# ============================================================

@app.get(
    "/terms",
    response_class=HTMLResponse
)
async def terms():

    return HTMLResponse(
        "<h2>Términos - CUBIKA TRAFFIC BOT</h2>"
        "<p>La aplicación se utiliza para integrar "
        "y medir actividades de marketing autorizadas.</p>"
    )
# ============================================================
# DIAGNOSTICO GA4
# ============================================================

@app.get("/ga4-debug")
async def ga4_debug():

    try:

        client = get_ga4_client()

        request = RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[
                DateRange(
                    start_date="2daysAgo",
                    end_date="today",
                )
            ],
            dimensions=[
                Dimension(name="date"),
                Dimension(name="sessionManualSource"),
                Dimension(name="sessionManualMedium"),
                Dimension(name="sessionManualCampaignName"),
                Dimension(name="sessionManualAdContent"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="activeUsers"),
            ],
            limit=100,
        )

        response = client.run_report(request)

        rows = []

        for row in response.rows:

            rows.append({
                "date": row.dimension_values[0].value,
                "source": row.dimension_values[1].value,
                "medium": row.dimension_values[2].value,
                "campaign": row.dimension_values[3].value,
                "content": row.dimension_values[4].value,
                "sessions": int(
                    float(row.metric_values[0].value or 0)
                ),
                "users": int(
                    float(row.metric_values[1].value or 0)
                ),
            })

        return {
            "connected": True,
            "property_id": GA4_PROPERTY_ID,
            "period": "2daysAgo - today",
            "rows": rows,
        }

    except Exception as error:

        return JSONResponse(
            {
                "connected": False,
                "error": str(error),
            },
            status_code=500
        )
# ============================================================
# GA4 REALTIME
# ============================================================

@app.get("/ga4-realtime")
async def ga4_realtime():

    try:

        client = get_ga4_client()

        request = {
            "property": f"properties/{GA4_PROPERTY_ID}",
            "dimensions": [
                {"name": "unifiedScreenName"},
                {"name": "country"},
            ],
            "metrics": [
                {"name": "activeUsers"},
                {"name": "screenPageViews"},
            ],
            "limit": 100,
        }

        response = client.run_realtime_report(
            request=request
        )

        rows = []

        for row in response.rows:

            rows.append({
                "screen": row.dimension_values[0].value,
                "country": row.dimension_values[1].value,
                "active_users": int(
                    float(row.metric_values[0].value or 0)
                ),
                "views": int(
                    float(row.metric_values[1].value or 0)
                ),
            })

        return {
            "connected": True,
            "property_id": GA4_PROPERTY_ID,
            "realtime": rows,
        }

    except Exception as error:

        return JSONResponse(
            {
                "connected": False,
                "property_id":
                    GA4_PROPERTY_ID or None,
                "error": str(error),
            },
            status_code=500
        )
