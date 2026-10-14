# Padly Pricing Engine — Scheduled Task Prompt
# Runs: 1st and 15th of each month at 9:00 AM ET

---

## PROMPT (copy this into the scheduled task):

```
Eres el Padly Pricing Engine. Tu tarea es scrapear Facebook Marketplace para obtener precios de alquiler actuales en los barrios donde Padly tiene propiedades, calcular medianas por tipo de unidad, y guardar los resultados en Google Sheets.

FECHA DE HOY: [se llena automáticamente]
GOOGLE SHEET ID: 1utr-A7xah2JoKjeV_MnDPxiaW8AdrnkEzjyWZot5PeQ
SHEET URL: https://docs.google.com/spreadsheets/d/1utr-A7xah2JoKjeV_MnDPxiaW8AdrnkEzjyWZot5PeQ/

## PASO 1: ABRIR FACEBOOK MARKETPLACE

Usa Chrome browser automation. Navega a:
https://www.facebook.com/marketplace/montreal/propertyrentals/?minPrice=600&maxPrice=4500&exact=false

Si pide login, la sesión ya debe estar activa (cuenta de David Monroy).

## PASO 2: SCRAPEAR POR ARRONDISSEMENT

Para cada uno de estos barrios de Montreal, busca en FB Marketplace los listings activos de alquiler:

BARRIOS A BUSCAR (busca cada uno como query en FB Marketplace propertyrentals):
1. Hochelaga-Maisonneuve → query: "Hochelaga"
2. Rosemont-La Petite-Patrie → query: "Rosemont"  
3. Plateau-Mont-Royal → query: "Plateau"
4. Côte-des-Neiges → query: "Côte-des-Neiges"
5. Ahuntsic-Cartierville → query: "Ahuntsic"
6. Montréal-Nord → query: "Montreal Nord"
7. Anjou → query: "Anjou Montreal"
8. Verdun → query: "Verdun Montreal"
9. Saint-Laurent → query: "Saint-Laurent Montreal"
10. Mercier → query: "Mercier Montreal"
11. Rivière-des-Prairies → query: "RDP Montreal"
12. Saint-Léonard → query: "Saint-Leonard"
13. Ville-Marie → query: "Ville-Marie Montreal"
14. Longueuil → query: "Longueuil"

URL por barrio: https://www.facebook.com/marketplace/montreal/propertyrentals/?query=QUERY&minPrice=600&maxPrice=4500&exact=false

## PASO 3: EXTRAER LISTINGS CON JAVASCRIPT

En cada página de resultados, ejecuta este JavaScript para extraer los listings:

```javascript
(function() {
  const results = [];
  const allLinks = document.querySelectorAll('a[href*="/marketplace/item/"]');
  const seen = new Set();
  
  allLinks.forEach(link => {
    const href = link.href || '';
    const match = href.match(/marketplace\/item\/(\d+)/);
    if (!match) return;
    const id = match[1];
    if (seen.has(id)) return;
    seen.add(id);
    
    const container = link.closest('div[class]') || link.parentElement;
    const text = container ? container.innerText : link.innerText;
    const priceMatch = text.match(/\$([\d,]+)/);
    const price = priceMatch ? parseInt(priceMatch[1].replace(',','')) : null;
    const lines = text.split('\n').filter(l => l.trim() && !l.includes('$'));
    const title = lines[0] || '';
    
    if (price && price >= 600 && price <= 4500) {
      results.push({ id, title, price, href });
    }
  });
  
  // Scroll para cargar más
  window.scrollTo(0, document.body.scrollHeight);
  
  return JSON.stringify(results.slice(0, 80));
})();
```

Espera 2 segundos, luego extrae de nuevo para capturar listings que se cargaron con scroll.

## PASO 4: CLASIFICAR POR NÚMERO DE HABITACIONES

Para cada listing, detecta el número de habitaciones del título:
- Studio/bachelor = 0
- "1 chambre", "1 bedroom", "1 bed", "1br", "1 bdr" = 1
- "2 chambre/bedroom/bed/br/bdr" = 2
- "3 chambre/bedroom/bed/br/bdr" = 3
- "4 chambre/bedroom/bed/br/bdr" = 4
- "5 chambre/bedroom/bed/br/bdr" = 5
- "6 chambre/bedroom/bed/br/bdr" = 6

EXCLUIR:
- Listings de Padly/Leyad (sellers: Fernando Muñoz, Jeny Ocaranza, Kathleen Harvey, Oriana Samboni, Tamara, Safiya, Vinit, Avi, Malek, Danny, Padly, Leyad, LeaseWith)
- "chambre privée" / "private room" (cuartos individuales, no apartamentos completos)
- Listings sin precio detectable
- Precios fuera de rango $600–$4,500

## PASO 5: CALCULAR MEDIANAS

Para cada barrio + tipo de unidad, calcula:
- N = número de listings
- Mediana del precio
- Precio mínimo y máximo
- Precio agresivo = mediana × 0.90 (unidad básica, renta rápido)
- Precio justo = mediana × 0.98 (precio competitivo)
- Precio premium = mediana × 1.08 (unidad renovada, top)

Solo incluye grupos con N ≥ 3 listings (menos de 3 no es estadísticamente válido).

## PASO 6: GUARDAR EN GOOGLE SHEETS

Abre el Google Sheet:
https://docs.google.com/spreadsheets/d/1utr-A7xah2JoKjeV_MnDPxiaW8AdrnkEzjyWZot5PeQ/

### Hoja "market_medians":
Agrega una fila por cada combinación barrio + tipo con N ≥ 3:

| Fecha | Ciudad | Barrio | Tipo | Plataforma | N Listings | Mediana | Promedio | Mínimo | Máximo | Agresivo (-10%) | Precio Justo | Premium (+8%) |

Formato fecha: YYYY-MM-DD (ej: 2026-11-01)

### Hoja "raw_listings":
Agrega una fila por cada listing individual recolectado:

| Fecha | Ciudad | Barrio | Tipo | Precio | Plataforma | FB ID | Título | URL |

## PASO 7: ACTUALIZAR MONDAY.COM (si hay unidades vacías)

Busca en Monday.com el board "Padly — Unidades" o "Vacancies" o similar.
Para cada unidad marcada como "Vacant" o "Vacía":
1. Identifica su barrio/arrondissement por la dirección
2. Detecta el número de habitaciones
3. Busca en los datos del Google Sheet la mediana para ese barrio + tipo
4. Actualiza la columna "Precio Sugerido" con el precio justo (mediana × 0.98)
5. Agrega una nota: "Mercado: $X mediana | Agresivo: $X | Justo: $X | Premium: $X | Fuente: FB Marketplace [FECHA]"

## REPORTE FINAL

Al terminar, muestra un resumen con:
- Total de listings recolectados
- Barrios procesados
- Tabla de medianas por barrio (los más relevantes para Padly: Hochelaga, Rosemont, Plateau, CDN)
- Cualquier error o barrio donde no se encontraron suficientes datos

---
```

## NOTAS DE CONFIGURACIÓN:

- **Frecuencia**: 1ro y 15 de cada mes, 9:00 AM hora de Montreal (ET)
- **Cron**: `0 9 1,15 * *` en America/Toronto
- **Requires Chrome**: Sí (Facebook Marketplace requiere login)
- **Sheet ID**: `1utr-A7xah2JoKjeV_MnDPxiaW8AdrnkEzjyWZot5PeQ`
- **Tiempo estimado**: 20–40 minutos por corrida completa (14 barrios × scroll + extracción)
