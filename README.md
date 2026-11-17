# TPI SO - Simulador de Planificación de CPU y Asignación de Memoria

Trabajo Práctico Integrador de **Sistemas Operativos** - UTN Facultad Regional Resistencia.

Simula un procesador con memoria de **particiones variables (MVT)**:

- 550K de memoria: 100K para el SO y 450K para procesos de usuario.
- Asignación **Best-Fit**.
- Planificación **SRTF** (expropiativo).
- Grado de multiprogramación máximo 5, hasta 10 procesos por simulación.

## Cómo usarlo

### Ejecutable (Windows, no requiere Python)

Abrir `SimuladorMVT.exe`. Los lotes de prueba están en la carpeta `lotes/`, al
lado del ejecutable.

### Desde el código

Requiere Python 3 (Tkinter viene incluido en el instalador de Windows).

| Comando | Qué hace |
|---|---|
| `python interfaz.py` | Interfaz gráfica |
| `python -m pytest` | Corre los tests (requiere `pytest`) |

Si `python` no se encuentra, usar `py` (por ejemplo `py interfaz.py`).

### Generar el ejecutable

```
python -m pip install pytest pyinstaller
powershell -ExecutionPolicy Bypass -File build.ps1
```

El script corre los tests y, si pasan, genera `dist\SimuladorMVT.exe` con
PyInstaller. Después copia `lotes/` y `README.pdf` a `dist\`. Para entregar,
comprimir la carpeta `dist\` completa.

## Archivo de entrada

- Solo se aceptan archivos `.csv`, con un proceso por línea: Id, tamaño (K),
  arribo e irrupción.
- Separador: coma, punto y coma, tabulación o espacios.
- El encabezado es opcional. Si está, las columnas pueden venir en cualquier
  orden (por ejemplo `Proceso,TA,TI,Tamaño`, como en los lotes de la cátedra).
  Si no está, el orden es Id, tamaño, arribo, irrupción.
- Los Id numéricos se convierten a `P` + número (`3` → `P3`).

Los procesos con errores (más de 450K, valores no numéricos, Id repetido, etc.)
**no frenan la carga**: se informan y se pregunta si se sigue con los válidos.
Si hay más de 10, se toman los 10 primeros del archivo.

## Lotes de prueba

| Lote | Qué prueba | TRP | TEP | Tiempo total |
|---|---|---|---|---|
| 1 | Arribos espaciados, CPU ociosa | 2,60 | 0,40 | 22 |
| 2 | Todos en T=0, procesos suspendidos | 26,20 | 15,00 | 56 |
| 3 | Más de 5 procesos simultáneos | 20,00 | 13,12 | 55 |
| 4 | 10 procesos con expropiaciones | 15,90 | 10,30 | 56 |
| 5 | P2 de 451K (se descarta; se simulan P1 y P3) | 6,00 | 1,50 | 9 |
| 6 | 12 procesos (se toman P1 a P10) | 19,40 | 14,90 | 45 |

## Reglas de la simulación

En cada instante T, en este orden:

1. **Ejecución** de la unidad anterior [T-1, T). Si el proceso en CPU termina,
   su finalización es T, libera su partición y los huecos vecinos se fusionan.
2. **Arribos:** los procesos con TA = T pasan a Nuevo (por orden de Id).
3. **Admisión:**
   - Los Listos y Suspendidos que ahora entran en algún hueco (en orden FIFO)
     reciben memoria y pasan a Listo. Ya cuentan para el grado de
     multiprogramación, así que no ocupan cupo nuevo. Si uno no entra, los que
     vienen detrás igual pueden entrar.
   - Mientras Ejecución + Listos + Suspendidos sea menor que 5, los Nuevos
     (FIFO) pasan a Listo si hay hueco, o a Listo y Suspendido si no lo hay.
4. **Planificación SRTF** entre el proceso en CPU y los Listos.

Lo que se muestra en el instante T es el estado después de esos pasos, es
decir, qué proceso usa la CPU durante [T, T+1). Un proceso que llega en T ya
aparece en la pantalla de T.



- **Desempates SRTF:** si un Listo empata con el que está en CPU, sigue el que
  está en CPU (solo se expropia con restante estrictamente menor). Entre
  Listos gana el de menor TA, y luego el de menor Id (P2 antes que P10).
- **Best-Fit:** el hueco más chico en el que entra el proceso; ante empate, el
  de menor dirección.
- **Sin swap-out:** un proceso solo va a Listo y Suspendido si no había hueco
  al admitirlo. Nunca se suspende un Listo para hacer lugar.
- **Fragmentación interna:** siempre 0K, porque en MVT cada partición se corta
  al tamaño exacto del proceso. La columna se muestra porque la consigna la
  pide.
- **Fragmentación externa:** se informa el total libre, la cantidad de huecos y
  el mayor, y se avisa cuando a un suspendido le alcanza la memoria libre total
  pero no entra en ningún hueco.
- **Alerta SRTF:** se muestra cuando el proceso que toma la CPU expropia al que
  estaba, o pasa delante de Listos que llegaron antes.
- **Estadísticas:** retorno = fin − TA; espera = retorno − TI;
  rendimiento = procesos terminados / tiempo total (fin del último, desde T = 0).

## Organización del código

| Archivo | Contenido |
|---|---|
| `constantes.py` | Valores de la consigna (memoria y límites) |
| `memoria.py` | MVT: Best-Fit, asignación, liberación con fusión de huecos, tabla de particiones |
| `planificador.py` | SRTF: elección del proceso en CPU y desempates |
| `simulacion.py` | Motor: estado, arribos, admisión, planificación, ejecución y estadísticas |
| `entrada.py` | Lectura y validación del CSV y del formulario |
| `informe.py` | Texto del informe estadístico (exportación a TXT) |
| `interfaz.py` | Interfaz gráfica (Tkinter) |
| `lotes/` | Los 6 lotes de prueba de la cátedra |
| `tests/` | Tests con pytest |

La simulación (`simulacion.py`, `memoria.py`, `planificador.py`) no importa
nada de la interfaz. Todo su estado vive en un único diccionario `estado` que se
pasa a cada función; la interfaz gráfica solo llama a esas funciones y muestra
el `estado`. Para "Ciclo Anterior", guarda una copia del `estado` antes de
cada avance.
