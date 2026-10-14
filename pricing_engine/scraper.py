"""
Padly Pricing Engine — FB Marketplace Scraper
=============================================
Busca listings en Facebook Marketplace por barrio/arrondissement,
calcula medianas por tipo de unidad, y guarda en Google Sheets.

Requiere: Chrome abierto con Claude in Chrome extension activa
          y sesión de Facebook iniciada (cuenta personal David Monroy)

Uso:
  python3 scraper.py --city montreal
  python3 scraper.py --city all
  python3 scraper.py --neighborhood "Hochelaga-Maisonneuve"
"""

import json, re, time, statistics, datetime
from pathlib import Path

# ─── Google Sheets ID ─────────────────────────────────────────────────────────
SHEET_ID = "1utr-A7xah2JoKjeV_MnDPxiaW8AdrnkEzjyWZot5PeQ"

# ─── Padly agent seller names (EXCLUIR de los resultados) ─────────────────────
PADLY_SELLERS = {
    "Padly", "Leyad", "Fernando Muñoz", "Jeny Ocaranza", "Kathleen Harvey",
    "Oriana Samboni", "Tamara", "Safiya Ali", "Vinit", "Avi", "Abhi",
    "LeaseWith", "Danny Chugunov", "Malek", "Winnipeg Wingspan",
}

# ─── Ciudades y sus barrios con parámetros de búsqueda ────────────────────────
CITIES = {
    "montreal": {
        "fb_city": "montreal",
        "fb_city_id": "C2MTNsVERNS",  # FB Marketplace city ID for Montreal
        "neighborhoods": [
            # (nombre_display, search_term, arrondissement_oficial)
            ("Hochelaga-Maisonneuve", "Hochelaga", "Hochelaga-Maisonneuve"),
            ("Rosemont-La Petite-Patrie", "Rosemont", "Rosemont-La Petite-Patrie"),
            ("Plateau-Mont-Royal", "Plateau", "Le Plateau-Mont-Royal"),
            ("Côte-des-Neiges-NDG", "Côte-des-Neiges", "Côte-des-Neiges-NDG"),
            ("Ahuntsic-Cartierville", "Ahuntsic", "Ahuntsic-Cartierville"),
            ("Montréal-Nord", "Montréal-Nord", "Montréal-Nord"),
            ("Anjou", "Anjou", "Anjou"),
            ("Verdun", "Verdun", "Verdun"),
            ("Saint-Laurent", "Saint-Laurent", "Saint-Laurent"),
            ("Mercier-Hochelaga", "Mercier", "Mercier-Hochelaga-Maisonneuve"),
            ("Rivière-des-Prairies", "RDP", "Rivière-des-Prairies-Pointe-aux-Trembles"),
            ("Saint-Léonard", "Saint-Léonard", "Saint-Léonard"),
            ("Ville-Marie", "Ville-Marie", "Ville-Marie"),
            ("Outremont", "Outremont", "Outremont"),
            ("Mont-Royal", "Mont-Royal", "Mont-Royal"),
            ("Westmount", "Westmount", "Westmount"),
            ("Côte-Saint-Luc", "Côte-Saint-Luc", "Côte-Saint-Luc"),
            ("Longueuil", "Longueuil", "Longueuil"),
        ]
    },
    "prince_albert": {
        "fb_city": "prince-albert-sk",
        "neighborhoods": [
            ("Prince Albert", "Prince Albert", "Prince Albert"),
        ]
    },
    "edmonton": {
        "fb_city": "edmonton",
        "neighborhoods": [
            ("Edmonton Nord-Est", "Edmonton", "Edmonton Nord-Est"),
            ("Edmonton Centre", "Edmonton Centre", "Edmonton Centre"),
            ("Edmonton Ouest", "Edmonton Ouest", "Edmonton Ouest"),
        ]
    },
    "winnipeg": {
        "fb_city": "winnipeg",
        "neighborhoods": [
            ("Winnipeg", "Winnipeg", "Winnipeg"),
        ]
    },
    "saskatoon": {
        "fb_city": "saskatoon",
        "neighborhoods": [
            ("Saskatoon", "Saskatoon", "Saskatoon"),
        ]
    },
}

# ─── Precio mínimo/máximo para filtrar listings válidos ───────────────────────
PRICE_MIN = 600
PRICE_MAX = 4500

# ─── Regex para extraer bedrooms del título ───────────────────────────────────
BED_PATTERNS = [
    (0, re.compile(r'\bstudio\b', re.I)),
    (1, re.compile(r'\b1\s*(?:ch(?:ambre)?|bed(?:room)?|bdr|br)\b', re.I)),
    (2, re.compile(r'\b2\s*(?:ch(?:ambre)?|bed(?:room)?|bdr|br)\b', re.I)),
    (3, re.compile(r'\b3\s*(?:ch(?:ambre)?|bed(?:room)?|bdr|br)\b', re.I)),
    (4, re.compile(r'\b4\s*(?:ch(?:ambre)?|bed(?:room)?|bdr|br)\b', re.I)),
    (5, re.compile(r'\b5\s*(?:ch(?:ambre)?|bed(?:room)?|bdr|br)\b', re.I)),
    (6, re.compile(r'\b6\s*(?:ch(?:ambre)?|bed(?:room)?|bdr|br)\b', re.I)),
]

def guess_beds(title: str) -> int | None:
    """Intenta detectar número de habitaciones del título del listing."""
    for beds, pat in BED_PATTERNS:
        if pat.search(title):
            return beds
    return None

def extract_price(price_str: str) -> int | None:
    """Extrae precio numérico de un string como '$1,350/month' o '1350'."""
    nums = re.findall(r'\d+', price_str.replace(',', ''))
    if nums:
        p = int(nums[0])
        return p if PRICE_MIN <= p <= PRICE_MAX else None
    return None

def is_padly_seller(seller_name: str) -> bool:
    """Devuelve True si el listing pertenece a un agente de Padly."""
    for s in PADLY_SELLERS:
        if s.lower() in seller_name.lower():
            return True
    return False

# ─── URLs de búsqueda en FB Marketplace ───────────────────────────────────────
def fb_search_url(city: str, query: str = "") -> str:
    """
    Genera URL de búsqueda en FB Marketplace para alquileres en una ciudad.
    FB Marketplace filtra por ubicación automáticamente si el usuario está logueado.
    """
    base = f"https://www.facebook.com/marketplace/{city}/propertyrentals/"
    params = f"?minPrice={PRICE_MIN}&maxPrice={PRICE_MAX}&exact=false"
    if query:
        params += f"&query={query.replace(' ', '%20')}"
    return base + params

# ─── Instrucciones JS para extraer listings de FB Marketplace ─────────────────
# Este código se ejecuta en el browser via javascript_tool
EXTRACT_LISTINGS_JS = """
(function() {
  const results = [];

  // FB Marketplace listings son divs con aria-label o data-testid específico
  // Buscamos las tarjetas de listing visibles
  const cards = document.querySelectorAll('[data-testid="marketplace_pdp_listing_card"]');

  // Fallback: buscar por estructura de precio + título
  const allLinks = document.querySelectorAll('a[href*="/marketplace/item/"]');
  const seen = new Set();

  allLinks.forEach(link => {
    const href = link.href || '';
    const match = href.match(/marketplace\\/item\\/(\\d+)/);
    if (!match) return;
    const id = match[1];
    if (seen.has(id)) return;
    seen.add(id);

    const container = link.closest('div[class]') || link.parentElement;
    const text = container ? container.innerText : link.innerText;

    // Buscar precio en el texto del contenedor
    const priceMatch = text.match(/\\$([\\d,]+)/);
    const price = priceMatch ? parseInt(priceMatch[1].replace(',','')) : null;

    // Título: primera línea de texto no-precio
    const lines = text.split('\\n').filter(l => l.trim() && !l.includes('$'));
    const title = lines[0] || '';

    if (price && price >= 600 && price <= 4500) {
      results.push({ id, title, price, href });
    }
  });

  return JSON.stringify(results.slice(0, 60));
})();
"""

EXTRACT_LISTING_DETAIL_JS = """
(function() {
  const t = document.body.innerText;

  // Precio
  const priceM = t.match(/\\$([\\d,]+)\\s*\\/\\s*month/i) || t.match(/\\$([\\d,]+)/);
  const price = priceM ? parseInt(priceM[1].replace(',','')) : null;

  // Título/descripción
  const titleEl = document.querySelector('h1') || document.querySelector('[data-testid="marketplace_pdp_title"]');
  const title = titleEl ? titleEl.innerText.trim() : '';

  // Vendedor
  const sellerSection = t.slice(Math.max(0, t.indexOf('Seller')), t.indexOf('Seller') + 200);
  const sellerLines = sellerSection.split('\\n').filter(l => l.trim());
  const seller = sellerLines[1] || '';

  // Dirección
  const addrMatch = t.match(/📍([^\\n]+)/);
  const address = addrMatch ? addrMatch[1].trim() : '';

  // Bedrooms del título
  const bedPatterns = [
    [0, /studio/i],
    [1, /1\\s*(?:ch(?:ambre)?|bed(?:room)?|bdr)/i],
    [2, /2\\s*(?:ch(?:ambre)?|bed(?:room)?|bdr)/i],
    [3, /3\\s*(?:ch(?:ambre)?|bed(?:room)?|bdr)/i],
    [4, /4\\s*(?:ch(?:ambre)?|bed(?:room)?|bdr)/i],
    [5, /5\\s*(?:ch(?:ambre)?|bed(?:room)?|bdr)/i],
    [6, /6\\s*(?:ch(?:ambre)?|bed(?:room)?|bdr)/i],
  ];
  let beds = null;
  for (const [n, pat] of bedPatterns) {
    if (pat.test(title) || pat.test(t.slice(0,500))) { beds = n; break; }
  }

  // Detectar si es cuarto privado (EXCLUIR)
  const isRoom = /chambre\\s+priv[eé]|private\\s+room|habitaci[oó]n\\s+privad/i.test(t.slice(0,1000));

  return JSON.stringify({ price, title, seller, address, beds, isRoom });
})();
"""

# ─── Cálculo de métricas de mercado ───────────────────────────────────────────
def calculate_market_stats(prices: list[int]) -> dict:
    """Calcula estadísticas de mercado para un conjunto de precios."""
    if not prices:
        return {}
    sorted_p = sorted(prices)
    n = len(sorted_p)
    return {
        "count": n,
        "median": int(statistics.median(sorted_p)),
        "mean": int(statistics.mean(sorted_p)),
        "min": sorted_p[0],
        "max": sorted_p[-1],
        "p25": sorted_p[n // 4],
        "p75": sorted_p[(3 * n) // 4],
    }

def pricing_suggestions(median: int) -> dict:
    """Genera los 3 precios sugeridos basados en la mediana."""
    return {
        "agresivo": int(median * 0.90),   # 10% abajo — renta rápido
        "justo":    int(median * 0.98),   # -2% — precio competitivo
        "premium":  int(median * 1.08),   # +8% — unidad renovada/top
    }

# ─── Formato de fila para Google Sheets ───────────────────────────────────────
def sheet_row(date: str, city: str, neighborhood: str, beds: int,
              stats: dict, platform: str = "Facebook Marketplace") -> list:
    bed_label = "Studio" if beds == 0 else f"{beds} hab."
    sugg = pricing_suggestions(stats["median"])
    return [
        date,
        city,
        neighborhood,
        bed_label,
        platform,
        stats["count"],
        stats["median"],
        stats["mean"],
        stats["min"],
        stats["max"],
        sugg["agresivo"],
        sugg["justo"],
        sugg["premium"],
    ]

SHEET_HEADERS = [
    "Fecha", "Ciudad", "Barrio/Arrondissement", "Tipo", "Plataforma",
    "N Listings", "Mediana", "Promedio", "Mínimo", "Máximo",
    "💰 Agresivo (-10%)", "✅ Precio Justo", "⭐ Premium (+8%)"
]

# ─── Script de configuración inicial del Google Sheet ─────────────────────────
# Ejecutar una sola vez para crear las hojas y headers
SHEET_SETUP_INSTRUCTIONS = """
Para configurar el Google Sheet:
1. Abrir: https://docs.google.com/spreadsheets/d/1utr-A7xah2JoKjeV_MnDPxiaW8AdrnkEzjyWZot5PeQ/
2. Renombrar "Sheet1" → "market_medians"
3. Agregar segunda hoja "raw_listings"
4. Agregar tercera hoja "pricing_suggestions"

Headers en market_medians (fila 1):
Fecha | Ciudad | Barrio/Arrondissement | Tipo | Plataforma | N Listings |
Mediana | Promedio | Mínimo | Máximo | 💰 Agresivo | ✅ Precio Justo | ⭐ Premium

Headers en raw_listings (fila 1):
Fecha | Ciudad | Barrio | Tipo | Precio | Plataforma | FB ID | Título | Dirección | Vendedor
"""

if __name__ == "__main__":
    print("Padly Pricing Engine — Scraper")
    print(f"Sheet: https://docs.google.com/spreadsheets/d/{SHEET_ID}/")
    print()
    print("Este script se ejecuta via Claude scheduled task con Chrome automation.")
    print("Ver: scraper_runner.py para el runner completo con browser control.")
    print()
    print(SHEET_SETUP_INSTRUCTIONS)

    # Test: mostrar URLs que se van a scrapear
    print("\n=== URLs de búsqueda para Montréal ===")
    for name, term, arr in CITIES["montreal"]["neighborhoods"]:
        url = fb_search_url("montreal", term)
        print(f"  {name}: {url}")
