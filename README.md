# Repositorio DIGITALPODER

Catálogo web de la bibliografía sobre digitalización, género y África del proyecto DIGITALPODER (PID2024-161343OB-I00, Universidad de Granada). La web se publica con GitHub Pages y se actualiza sola a partir de la matriz bibliográfica que el equipo mantiene en Google Drive.

## Cómo funciona

1. El equipo edita la matriz en Drive (`Matriz_bibliografica_DIGITALPODER.xlsm`).
2. Cada hora, una tarea automática de GitHub descarga la matriz, la convierte en `data/repositorio.json` y vuelve a publicar la web.
3. Si la matriz no ha cambiado, no se publica nada nuevo. Si la descarga falla, la web sigue mostrando la última versión buena.

Para ver un cambio sin esperar a la hora siguiente, entra en la pestaña **Actions** del repositorio, elige **Actualizar y publicar el repositorio** y pulsa **Run workflow**.

## Puesta en marcha (una sola vez)

1. **Crear el repositorio.** En GitHub, *New repository*, nombre `repositorio-digitalpoder`, visibilidad pública. Sube el contenido de esta carpeta (incluida la carpeta oculta `.github`).
2. **Compartir la matriz.** En Drive, botón *Compartir* de la matriz → *Acceso general* → *Cualquier persona con el enlace* → *Lector*.
3. **Guardar el identificador de la matriz.** Es la parte del enlace de Drive entre `/d/` y `/view`. En GitHub: *Settings* → *Secrets and variables* → *Actions* → *New repository secret*. Nombre `MATRIZ_DRIVE_ID`, valor el identificador.
4. **Activar Pages.** *Settings* → *Pages* → *Source*: **GitHub Actions**.
5. **Primera publicación.** *Actions* → *Actualizar y publicar el repositorio* → *Run workflow*. Al terminar, la web queda en `https://<usuario>.github.io/repositorio-digitalpoder/`.

## Reglas para que la actualización no se rompa

- **Editar siempre el mismo archivo de Drive.** Si se sube una matriz nueva como archivo aparte, cambia el identificador y la web deja de actualizarse. Para sustituirla por una versión trabajada en local, usa *Gestionar versiones* → *Subir nueva versión* sobre el archivo existente.
- **No cambiar el orden de las nueve primeras columnas** de las hojas de los ejes: País/Región, Año, Referencia corta, Título, Revista/Fuente, Tema clave, Método/Datos, Hallazgos clave, Enlace carpeta.
- **Mantener el comienzo del nombre de cada hoja** (Eje tecnológico, Emprendimiento…, Compatibilidad…, Estrategias…, Marco teórico…, Contextos, Documentación…). Se puede ampliar el nombre, pero no cambiar cómo empieza.
- Para que una ficha muestre el botón de DOI, basta con poner el enlace `https://doi.org/...` en la columna *Enlace carpeta* o incluir el DOI en la columna de la fuente.
- La hoja *Dudas* no se publica.

## Archivos

| Archivo | Qué es |
|---|---|
| `index.html` | La página web |
| `data/repositorio.json` | Datos que lee la página; lo genera la tarea automática |
| `data/referencias_complementarias.md` | 82 referencias verificadas con DOI. Las que aún no están en la matriz se añaden al catálogo. Cuando se incorporen a la matriz, este archivo se puede vaciar |
| `scripts/build_data.py` | Convierte la matriz en `repositorio.json` y clasifica cada ficha por eje, ámbito geográfico, tipo e idioma |
| `.github/workflows/actualizar.yml` | La tarea automática que descarga, convierte y publica |

## Probar en local

```
pip install openpyxl
python scripts/build_data.py ruta/a/Matriz_bibliografica_DIGITALPODER.xlsm
python -m http.server
```

y abrir `http://localhost:8000`.
