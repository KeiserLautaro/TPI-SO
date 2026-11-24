# TPI Sistemas Operativos — Equipo 9 (UTN FRRe)

Simulador de asignación de memoria con particiones variables (MVT, Best-Fit) y planificación
de CPU con SRTF. Python 3 + Tkinter. Todo en español (código, mensajes y documentación).

## Reglas de trabajo

- **No hacer commits ni push.** El usuario commitea; dejar los cambios sin commitear y, al
  terminar, decir qué archivos nuevos/borrados tiene que incluir.
- **Programación estructurada:** solo funciones y diccionarios, sin clases. Varios integrantes
  no vieron POO y todos tienen que poder explicar el código.
- **Nada de herramientas auxiliares en el repo ni en la entrega.** Scripts para generar PDFs,
  capturas, etc. van en el scratchpad, nunca en el proyecto. «Para el profesor nunca deberían
  haber existido.»
- Sin docstrings (se sacaron a pedido) y solo comentarios que aporten algo que el código no dice.
- Antes de dar algo por terminado: `python -m pytest` y, si cambió algo de la entrega,
  regenerar el build.

## Estructura

| Archivo | Contenido |
|---|---|
| `constantes.py` | Memoria (100K SO + 450K usuario), multiprogramación 5, máx. 10 procesos |
| `memoria.py` | MVT: Best-Fit, asignar (corte exacto), liberar con fusión, tabla, fragmentación |
| `planificador.py` | SRTF: `clave_srtf`, `elegir_proceso_srtf` y desempates |
| `simulacion.py` | Motor: diccionario `estado`, ciclo de un instante, avance, estadísticas |
| `entrada.py` | Lectura del CSV (solo `.csv`) y validación |
| `informe.py` | Texto del informe para «Exportar a TXT» (sin Gantt) |
| `interfaz.py` | GUI Tkinter (única interfaz; la consola se eliminó) |
| `tests/` | 42 tests con pytest; fijan los resultados de todos los lotes |
| `lotes/` | `lote_1`–`lote_6` de la cátedra, `lote_7`–`lote_11` propios del equipo |
| `capturas/` | 4 capturas de la app que usan el README y la documentación |
| `README.md` / `README.pdf` | Instructivo **para el usuario final** (cómo usar la app) |
| `docs/` | Documentación del código (`documentacion_codigo.html` → `.pdf`) y logo UTN |
| `build.ps1` | Tests → PyInstaller → `dist\` con `Simulador_Equipo9.exe`, `lotes\` y `README.pdf` |

El motor (`simulacion`, `memoria`, `planificador`) no importa nada de la interfaz.

## Comandos

```
python -m pytest
python interfaz.py
powershell -ExecutionPolicy Bypass -File build.ps1      # requiere: pip install pytest pyinstaller
```

La entrega es la carpeta `dist\` comprimida (la arma el usuario): `.exe`, `README.pdf` y `lotes\`.

## Reglas de la simulación (no cambiar sin acordarlo)

Orden en cada instante: ejecución [T-1,T) → arribos → admisión (primero Suspendidos que ahora
entran, sin bloquearse entre sí; después Nuevos mientras grado < 5) → SRTF. Expropia solo con
restante estrictamente menor; entre Listos desempata menor TA y luego menor número de Id
(P2 antes que P10). Best-Fit desempata por menor dirección. Sin swap-out. Más de 10 procesos:
se toman los 10 primeros (pendiente confirmar con la cátedra por el lote 6).

## Lotes

Formato: punto y coma, UTF-8 **con BOM**, fin de línea CRLF (así Excel en español los abre con
un dato por celda). El lector igual acepta coma, tabulación o espacios. Si se agrega o cambia un
lote: actualizar `ESPERADOS` en `tests/test_simulacion.py`, la tabla del README y la de la
sección 9.1 de la documentación.

## Documentación

### Instructivo (`README.md` → `README.pdf`)

Dirigido al usuario final: abrir el exe, cargar procesos, simular, informe, lotes, reglas.
Nada de cómo correr desde el código. `README.pdf` es un archivo fijo del repo: **si cambia el
README hay que regenerarlo** (y copiarlo a `dist\` o rehacer el build).

Se genera con un script fuera del repo (recrearlo en el scratchpad si no está): convierte el
Markdown a HTML (títulos, listas anidadas, tablas, código, negrita, imágenes `![Figura N: …](capturas/…)`
como `<figure>` con leyenda) y lo imprime con Edge headless:
`msedge --headless --disable-gpu --no-pdf-header-footer --user-data-dir=<tmp> --print-to-pdf=<pdf> file:///<html>`.
Estilo: el mismo CSS que `docs/documentacion_codigo.html` (serif Cambria, azul `#1f3864`,
tablas con encabezado `#dfe5ee`, figuras con borde y leyenda), sin portada.

### Documentación del código (`docs/documentacion_codigo.html`)

Es la **fuente editable**; el PDF se genera desde ahí. Tiene portada, índice, arquitectura,
estructuras de datos, algoritmos con código real, tablas de funciones por módulo, pruebas,
build y decisiones de diseño. Las partes a completar están marcadas con
`<span class="completar">` (resaltado amarillo): carrera, integrantes y legajos, docentes,
comisión, fecha, requerimientos faltantes del enunciado, confirmación del lote 6 y
conclusiones. Al completarlas, sacar el `span`.

Regenerar el PDF (PowerShell, desde la raíz del repo):

```
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
$html = (Resolve-Path docs\documentacion_codigo.html).Path
$pdf = Join-Path (Resolve-Path docs).Path "documentacion_codigo.pdf"
Start-Process -FilePath $edge -Wait -ArgumentList @("--headless", "--disable-gpu", "--no-pdf-header-footer", "--user-data-dir=`"$env:TEMP\edge_pdf`"", "--print-to-pdf=`"$pdf`"", ("file:///" + $html.Replace('\','/')))
```

Detalles de Edge que costó resolver:
- El encabezado usa `@page` margin boxes. El logo va como SVG en data URI (envuelve el PNG a
  160×56); un archivo externo o un PNG directo no funcionan (no se puede escalar).
- La portada no tiene encabezado, así que el logo se **precarga** con un `<img>` invisible en la
  portada; si se quita, el logo no aparece en las demás páginas.
- Lanzar Edge con `Start-Process -Wait`; llamado directo vuelve antes de escribir el PDF.
- Al copiar texto del PDF aparecen «í» sueltas; en pantalla e impreso se ve bien.

Si cambia el código, revisar en la documentación: cantidad de líneas por módulo (sección 3.2),
cantidad de tests (sección 9), tablas de funciones (sección 6) y fragmentos de código citados.

### Capturas (`capturas/`)

Se sacan con un script fuera del repo que importa `interfaz`, reemplaza `tk.Tk.mainloop` por
una función vacía, llama a `main()`, carga lotes con `cargar_archivo()`, avanza con
`ejecutar_paso_a_paso()` y captura la ventana con `PrintWindow` (proceso con
`SetProcessDpiAwareness(2)`, recorte con `DwmGetWindowAttribute` para sacar la sombra, PNG escrito
con `zlib`, sin dependencias). Capturas actuales: 01 carga (lote 4), 02 simulación lote 4 en
T=8, 03 informe final lote 4, 04 lote 7 en T=5.

## Pendientes

- Completar los campos marcados de `docs/documentacion_codigo.html` y regenerar el PDF.
- Confirmar con la cátedra qué hacer con más de 10 procesos (lote 6).
- Probar el `.exe` a mano antes de entregar.
