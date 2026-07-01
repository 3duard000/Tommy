/**
 * TOMMY WHOLESALE RENTAL — Formulario de contacto -> Google Sheet
 * =============================================================================
 * Este codigo recibe los envios del formulario de la pagina web y los guarda
 * como filas en una Google Sheet.
 *
 * COMO INSTALARLO (una sola vez):
 *
 * 1) Crea una Google Sheet nueva (sheets.new). En la fila 1 escribe estos
 *    encabezados (una palabra por columna):
 *        A1: Fecha   B1: Nombre   C1: Telefono   D1: Email
 *        E1: Fecha del evento   F1: Tipo de evento   G1: Mensaje
 *
 * 2) En esa hoja: menu  Extensiones -> Apps Script.
 *
 * 3) Borra lo que haya y pega TODO este archivo. Guarda (icono de diskette).
 *
 * 4) Arriba a la derecha: boton  Implementar (Deploy) -> Nueva implementacion.
 *      - Tipo:  Aplicacion web (Web app)
 *      - Descripcion:  Formulario Tommy
 *      - Ejecutar como:  Yo (tu cuenta)
 *      - Quien tiene acceso:  Cualquier persona (Anyone)
 *    Da clic en  Implementar  y autoriza los permisos que pida.
 *
 * 5) Copia la  "URL de la aplicacion web"  que te da (termina en /exec).
 *
 * 6) En el archivo  index.html  de la pagina, reemplaza:
 *        const FORM_ENDPOINT = "PASTE_YOUR_APPS_SCRIPT_URL_HERE";
 *    por tu URL, por ejemplo:
 *        const FORM_ENDPOINT = "https://script.google.com/macros/s/AKfy.../exec";
 *    Sube el cambio y listo: los envios llegaran a tu hoja.
 *
 * (Si mas adelante cambias este codigo, usa Implementar -> Administrar
 *  implementaciones -> editar -> Nueva version, para que tome los cambios.)
 * =============================================================================
 */

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
    var p = (e && e.parameter) ? e.parameter : {};

    sheet.appendRow([
      new Date(),            // Fecha de recepcion
      p.name || '',          // Nombre
      p.phone || '',         // Telefono
      p.email || '',         // Email
      p.eventDate || '',     // Fecha del evento
      p.eventType || '',     // Tipo de evento
      p.message || ''        // Mensaje
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({ result: 'success' }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ result: 'error', error: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// Permite abrir la URL en el navegador para comprobar que esta activa.
function doGet() {
  return ContentService
    .createTextOutput('Tommy Wholesale Rental form endpoint is running.')
    .setMimeType(ContentService.MimeType.TEXT);
}
