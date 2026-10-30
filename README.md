# Directorio de casas desarrolladoras de software

Aplicación web local en Flask + MongoDB. Permite buscar por nombre o fragmento, ver fichas y completar el CRUD (crear, consultar, actualizar y eliminar). El distintivo de cada ficha lleva al sitio oficial cuando se registra una URL.

## Requisitos

- Python 3.10 o superior.
- MongoDB Community Server iniciado localmente en el puerto 27017.

## Inicio en Windows (PowerShell)

Abre PowerShell en esta carpeta y ejecuta, línea por línea:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
py seed.py
py app.py
```

Si PowerShell bloquea la activación del entorno virtual, ejecuta `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` en esa ventana y vuelve a activar. Para verificar MongoDB, abre **Servicios** de Windows y confirma que el servicio **MongoDB Server** esté en ejecución. Si instalaste MongoDB en modo consola, inicia `mongod` en otra terminal antes de usar la aplicación.

Abre http://127.0.0.1:5000 en el navegador. Deja abierta la terminal donde ejecutaste `py app.py` mientras usas el sitio. Para detenerlo, pulsa Ctrl+C.

## Cómo usar la aplicación

1. Escribe un nombre completo o parcial en el buscador; por ejemplo, `soft`, `meta` o `COD`.
2. Cada ficha muestra nombre, ubicación, especialidad y teléfono. El número permite iniciar una llamada desde dispositivos compatibles.
3. El botón **Nueva empresa** abre el formulario de alta.
4. Usa el lápiz para modificar una ficha o el botón de papelera para eliminarla.
5. Para que el distintivo de una empresa dirija a su página oficial, edítala, pega una URL completa con `https://` y guarda. Al hacer clic se abre en otra pestaña.

## Datos y colección

`seed.py` inserta las 15 empresas de la tabla en la base `directorio_software`, colección `casas`. La carga es idempotente: ejecutarla nuevamente no duplica las empresas ni sobrescribe los cambios existentes. No se inventaron URLs oficiales; se completan en las fichas tras verificar cada sitio. También se pueden añadir imágenes/logotipos más adelante agregando un campo para su URL o archivo.

La aplicación lee `MONGODB_URI` y `MONGODB_DATABASE` del archivo `.env`. Para una instalación local típica, los valores de `.env.example` funcionan sin autenticación.

## Estructura

- `app.py`: servidor Flask y endpoints CRUD.
- `seed.py`: carga de datos de ejemplo.
- `templates/index.html`: página principal y formulario.
- `static/styles.css`, `static/app.js`: interfaz y llamadas a la API.
