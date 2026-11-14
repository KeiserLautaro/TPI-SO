# TPI SO - Simulador de Planificación de CPU y Asignación de Memoria

Trabajo Práctico Integrador para la cátedra de **Sistemas Operativos** - **Universidad Tecnológica Nacional (UTN) - Facultad Regional Resistencia (FRRe)**.

Simula un procesador con memoria de **particiones variables (MVT)**: 100K para el
SO y 450K para procesos de usuario. Asignación **Best-Fit**, planificación
**SRTF** (expropiativo), grado de multiprogramación máximo 5 y hasta 10 procesos.

Implementado con **programación estructurada** (solo funciones, sin clases).

## Cómo ejecutar

**Ejecutable (Windows, no requiere Python):** abrir `SimuladorMVT.exe` con doble
clic. La carpeta `lotes/` tiene que estar al lado del ejecutable.

**Desde el código** (Python 3; Tkinter viene incluido en el instalador de Windows):

```
python interfaz.py                              interfaz gráfica
python consola.py lotes/lote_1.csv              consola, pausa en cada instante
python consola.py lotes/lote_1.csv --eventos    consola, pausa en arribos y terminaciones
python -m pytest                                tests
```

Si `python` no se encuentra, usar `py` (por ejemplo `py interfaz.py`).

## Generar el ejecutable

```
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File build.ps1
```

Corre los tests y, si pasan, genera `dist\SimuladorMVT.exe` con PyInstaller y
copia `lotes/` y este README a `dist\`. Para entregar, comprimir la carpeta
`dist\` completa. `build/` y `dist/` no se suben al repositorio.

## Organización del código

```
constantes.py     Valores de la consigna (memoria, límites)
memoria.py        MVT: Best-Fit, asignar, liberar con fusión de huecos, tabla de particiones
planificador.py   SRTF: elegir el proceso que ocupa la CPU y reglas de desempate
simulacion.py     Motor: estado, arribos, admisión, planificación, ejecución, estadísticas
entrada.py        Lectura y validación de archivos y del formulario
informe.py        Textos del estado, del informe y del Gantt (consola y exportación)
consola.py        Interfaz por consola
interfaz.py       Interfaz gráfica (Tkinter)
lotes/            Los 6 lotes de prueba de la cátedra
tests/            Tests con pytest
```

La simulación (`simulacion.py`, `memoria.py`, `planificador.py`) **no importa
nada de la interfaz**. Todo su estado está en un único diccionario `estado` que
se pasa a cada función. La consola y la interfaz gráfica solo llaman a esas
funciones y muestran el `estado`; por eso las dos dan siempre los mismos
resultados. Para "Ciclo Anterior", la interfaz guarda `copy.deepcopy(estado)`
antes de cada avance.

## Reglas de la simulación

En cada instante T, en este orden:

1. **Ejecución** de la unidad anterior [T-1, T). Si el proceso en CPU termina,
   su finalización es T, libera su partición y los huecos vecinos se fusionan.
2. **Arribos:** los procesos con TA = T pasan a Nuevo (por orden de Id).
3. **Admisión:**
   - Los Listos/Suspendidos, en orden FIFO, que ahora entran en algún hueco
     reciben memoria y pasan a Listo. Ya cuentan para el grado de
     multiprogramación, así que no consumen cupo. Si uno no entra, los de
     atrás igual pueden entrar.
   - Mientras Ejecución + Listos + Suspendidos < 5, los Nuevos (FIFO) pasan a
     Listo si hay hueco, o a Listo/Suspendido si no lo hay.
4. **Planificación SRTF** entre el proceso en CPU y los Listos.

**Lo que se muestra en el instante T** es el estado después de esos pasos: qué
proceso usa la CPU durante [T, T+1). Un proceso que llega en T ya aparece en la
pantalla de T.

Supuestos (la consigna no los especifica):

- **Desempates SRTF:** si un Listo empata con el que está en CPU, sigue el que
  está en CPU (solo se expropia con restante estrictamente menor). Entre
  Listos, gana el de menor TA y luego el de menor Id (P2 antes que P10).
- **Best-Fit:** hueco de menor tamaño suficiente; ante empate, el de menor dirección.
- **No hay swap-out:** un proceso solo va a Listo/Suspendido si no había hueco
  al admitirlo. Nunca se suspende un Listo para hacer lugar.
- **Fragmentación interna:** siempre 0K, porque en MVT cada partición se corta
  al tamaño exacto del proceso. Se muestra la columna porque la consigna la
  pide. La fragmentación que sí aparece es la **externa**: se informa el total
  libre, la cantidad de huecos y el mayor, y se avisa cuando a un suspendido le
  alcanza la memoria libre total pero no entra en ningún hueco.
- **Alerta SRTF:** cuando el proceso que toma la CPU expropia al que estaba, o
  pasa delante de Listos que llegaron antes.
- **Estadísticas:** retorno = fin − TA; espera = retorno − TI;
  rendimiento = procesos terminados / tiempo total (fin del último, desde T = 0).

## Archivo de entrada

Un proceso por línea: Id, tamaño (K), arribo, irrupción. Se acepta coma, punto
y coma, tabulación o espacios como separador. El encabezado es opcional; si
está, las columnas pueden venir en cualquier orden (por ejemplo
`Proceso,TA,TI,Tamaño`, como en los lotes de la cátedra). Los Id numéricos se
convierten a `P` + número.

Los procesos con errores (más de 450K, valores no numéricos, Id repetido, etc.)
**no frenan la carga**: se informan y se pregunta si se continúa con los
válidos. Si hay más de 10, se toman los 10 primeros del archivo.

| Lote | Qué prueba | TRP | TEP | Tiempo total |
|---|---|---|---|---|
| 1 | Arribos espaciados, CPU ociosa | 2.60 | 0.40 | 22 |
| 2 | Todos en T=0, procesos suspendidos | 26.20 | 15.00 | 56 |
| 3 | Más de 5 procesos simultáneos | 20.00 | 13.12 | 55 |
| 4 | 10 procesos con expropiaciones | 15.90 | 10.30 | 56 |
| 5 | P2 de 451K (se descarta, se simulan P1 y P3) | 6.00 | 1.50 | 9 |
| 6 | 12 procesos (se toman P1 a P10) | 19.40 | 14.90 | 45 |
