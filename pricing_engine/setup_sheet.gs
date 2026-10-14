/**
 * Padly Pricing Engine — Google Apps Script Setup
 *
 * INSTRUCCIONES:
 * 1. Abre el Google Sheet: https://docs.google.com/spreadsheets/d/1utr-A7xah2JoKjeV_MnDPxiaW8AdrnkEzjyWZot5PeQ/
 * 2. Ve a Extensions > Apps Script
 * 3. Pega este código completo
 * 4. Haz clic en "Run" > "setupPricingEngine"
 * 5. Autoriza los permisos cuando te lo pida
 * 6. ¡Listo! Las 3 hojas quedarán configuradas con sus headers
 */

function setupPricingEngine() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // ── 1. market_medians ──────────────────────────────────────────────────────
  let sheet1 = ss.getSheetByName('market_medians');
  if (!sheet1) {
    sheet1 = ss.getActiveSheet();
    sheet1.setName('market_medians');
  }

  const headers1 = [
    'Fecha', 'Ciudad', 'Barrio/Arrondissement', 'Tipo', 'Plataforma',
    'N Listings', 'Mediana', 'Promedio', 'Mínimo', 'Máximo',
    '💰 Agresivo (-10%)', '✅ Precio Justo (-2%)', '⭐ Premium (+8%)'
  ];
  sheet1.getRange(1, 1, 1, headers1.length).setValues([headers1]);
  sheet1.getRange(1, 1, 1, headers1.length)
    .setBackground('#1a1a2e')
    .setFontColor('#ffffff')
    .setFontWeight('bold');
  sheet1.setFrozenRows(1);
  sheet1.setColumnWidth(3, 220); // Barrio col wider

  // Format currency columns (Mediana, Promedio, Min, Max, Agresivo, Justo, Premium)
  const currencyCols = [7, 8, 9, 10, 11, 12, 13];
  currencyCols.forEach(col => {
    sheet1.getRange(2, col, 999).setNumberFormat('"$"#,##0');
  });

  // ── 2. raw_listings ────────────────────────────────────────────────────────
  let sheet2 = ss.getSheetByName('raw_listings');
  if (!sheet2) sheet2 = ss.insertSheet('raw_listings', 1);

  const headers2 = [
    'Fecha', 'Ciudad', 'Barrio', 'Tipo', 'Precio', 'Plataforma',
    'FB ID', 'Título', 'URL'
  ];
  sheet2.getRange(1, 1, 1, headers2.length).setValues([headers2]);
  sheet2.getRange(1, 1, 1, headers2.length)
    .setBackground('#0f3460')
    .setFontColor('#ffffff')
    .setFontWeight('bold');
  sheet2.setFrozenRows(1);
  sheet2.setColumnWidth(8, 300); // Título wider
  sheet2.setColumnWidth(9, 250); // URL wider
  sheet2.getRange(2, 5, 999).setNumberFormat('"$"#,##0'); // Precio

  // ── 3. pricing_suggestions ─────────────────────────────────────────────────
  let sheet3 = ss.getSheetByName('pricing_suggestions');
  if (!sheet3) sheet3 = ss.insertSheet('pricing_suggestions', 2);

  const headers3 = [
    'Fecha', 'Ciudad', 'Barrio', 'Dirección (Monday)', 'Tipo Unidad',
    'Mediana Mercado', '💰 Precio Agresivo', '✅ Precio Justo', '⭐ Precio Premium',
    'Precio Actual (Monday)', 'Diferencia vs Justo', 'Estado', 'Notas'
  ];
  sheet3.getRange(1, 1, 1, headers3.length).setValues([headers3]);
  sheet3.getRange(1, 1, 1, headers3.length)
    .setBackground('#16213e')
    .setFontColor('#ffffff')
    .setFontWeight('bold');
  sheet3.setFrozenRows(1);
  sheet3.setColumnWidth(4, 250); // Dirección wider
  const currencyCols3 = [6, 7, 8, 9, 10, 11];
  currencyCols3.forEach(col => {
    sheet3.getRange(2, col, 999).setNumberFormat('"$"#,##0');
  });

  // ── Agregar fórmula de estado en pricing_suggestions ──────────────────────
  // Fórmula: si precio actual es 0, "Sin precio"; si está abajo del agresivo, "Muy Barato"; etc.
  sheet3.getRange('L2').setFormula(
    '=IF(J2=0,"Sin precio",IF(J2<G2,"🔴 Muy Barato",IF(J2<H2,"🟡 Por Debajo del Mercado",IF(J2<=I2,"✅ Precio Justo","⭐ Premium"))))'
  );

  SpreadsheetApp.flush();

  Browser.msgBox(
    '✅ Padly Pricing Engine configurado',
    'Las 3 hojas fueron creadas:\\n\\n' +
    '• market_medians: medianas por barrio\\n' +
    '• raw_listings: todos los listings individuales\\n' +
    '• pricing_suggestions: precios sugeridos para unidades vacías\\n\\n' +
    'El scraper automático correrá el 1 y 15 de cada mes.',
    Browser.Buttons.OK
  );
}

/**
 * Función helper para escribir datos de mercado programáticamente.
 * El scheduled task de Claude llama funciones similares via la API.
 */
function appendMarketData(date, city, neighborhood, type, platform,
                           count, median, mean, min, max) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('market_medians');
  const aggressive = Math.round(median * 0.90);
  const fair = Math.round(median * 0.98);
  const premium = Math.round(median * 1.08);

  sheet.appendRow([
    date, city, neighborhood, type, platform,
    count, median, mean, min, max,
    aggressive, fair, premium
  ]);
}
