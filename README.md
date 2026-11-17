# TPI SO - Simulador de Planificación de CPU y Asignación de Memoria

Trabajo Práctico Integrador de **Sistemas Operativos** - UTN Facultad Regional Resistencia.

Simula un procesador con memoria de **particiones variables (MVT)**:

- 550K de memoria: 100K para el SO y 450K para procesos de usuario.
- Asignación **Best-Fit**.
- Planificación **SRTF** (expropiativo).
- Grado de multiprogramación máximo 5, hasta 10 procesos por simulación.

## Cómo abrirlo

Abrir `Simulador_Equipo9.exe` con doble clic (Windows, no requiere instalar nada).
Los lotes de prueba están en la carpeta `lotes`, al lado del ejecutable.

## 1. Cargar los procesos

La primera pantalla tiene dos formas de cargar procesos, que se pueden combinar:

- **Opción A - Archivo CSV:** el botón **Seleccionar Archivo CSV** abre la
  carpeta `lotes`. Al elegir un archivo, sus procesos reemplazan a los que
  estaban cargados.
- **Opción B - Carga manual:** completar Id, tamaño, tiempo de arribo y tiempo
  de irrupción, y apretar **Agregar Proceso a la Lista**.

La tabla de la derecha muestra los procesos cargados (máximo 10).
**Eliminar Seleccionado** quita el proceso marcado y **Limpiar Todo** vacía la
lista. Cuando estén listos, apretar **INICIAR SIMULACIÓN CON ESTOS PROCESOS**.

### Formato del archivo CSV

- Un proceso por línea: Id, tamaño (K), arribo e irrupción.
- Separador: punto y coma (como guarda Excel en español), coma, tabulación o
  espacios. Los lotes usan punto y coma, así que en Excel se ven con un dato
  por celda.
- El encabezado es opcional. Si está, las columnas pueden venir en cualquier
  orden (por ejemplo `Proceso;TA;TI;Tamaño`, como en los lotes de la cátedra).
  Si no está, el orden es Id, tamaño, arribo, irrupción.
- Los Id numéricos se convierten a `P` + número (`3` → `P3`).

Los procesos con errores (más de 450K, valores no numéricos, Id repetido, etc.)
**no frenan la carga**: se informan y se pregunta si se sigue con los válidos.
Si hay más de 10, se toman los 10 primeros del archivo.

## 2. Simular

La simulación arranca en T = 0. Botones de la barra inferior:

| Botón | Qué hace |
|---|---|
| **Ciclo Anterior** | Vuelve al instante anterior (también con la flecha ←) |
| **Siguiente Ciclo (T + 1)** | Avanza un instante (también con la flecha →) |
| **Siguiente Evento (Arribo/Fin)** | Avanza hasta que llega o termina un proceso |
| **Reiniciar (T=0)** | Vuelve al principio con los mismos procesos |
| **Informe Estadístico** | Muestra las métricas hasta el momento |
| **Volver a Inicio / Carga** | Regresa a la pantalla de carga de procesos |

Qué muestra la pantalla en cada instante:

- **Arriba:** el tiempo T y, en amarillo, la alerta SRTF cuando un proceso
  expropia la CPU o pasa delante de otros que llegaron antes.
- **Izquierda:** el proceso en CPU, el grado de multiprogramación y las colas
  de Listos, Listos y Suspendidos, y Nuevos.
- **Derecha:** la tabla de particiones, la fragmentación externa, un gráfico de
  la memoria, el diagrama de Gantt y el registro de sucesos (los del último
  paso en negrita y las alertas en rojo).

## 3. Informe final

Cuando terminan todos los procesos se abre el informe estadístico: tiempo de
retorno y de espera de cada proceso, sus promedios, el tiempo total y el
rendimiento del sistema. **Exportar a TXT** lo guarda en un archivo de texto.

## Lotes de prueba

Resultados esperados de cada lote de la carpeta `lotes`:

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

Además:

- **Desempates SRTF:** si un Listo empata con el que está en CPU, sigue el que
  está en CPU (solo se expropia con restante estrictamente menor). Entre
  Listos gana el de menor TA, y luego el de menor Id (P2 antes que P10).
- **Best-Fit:** el hueco más chico en el que entra el proceso; ante empate, el
  de menor dirección.
- **Sin swap-out:** un proceso solo va a Listo y Suspendido si no había hueco
  al admitirlo. Nunca se suspende un Listo para hacer lugar.
- **Fragmentación interna:** siempre 0K, porque en MVT cada partición se corta
  al tamaño exacto del proceso.
- **Fragmentación externa:** se informa el total libre, la cantidad de huecos y
  el mayor, y se avisa cuando a un suspendido le alcanza la memoria libre total
  pero no entra en ningún hueco.
- **Estadísticas:** retorno = fin − TA; espera = retorno − TI;
  rendimiento = procesos terminados / tiempo total (fin del último, desde T = 0).
