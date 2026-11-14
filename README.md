# TPI SO - Simulador de Planificación de CPU y Asignación de Memoria

Trabajo Práctico Integrador para la cátedra de **Sistemas Operativos** - **Universidad Tecnológica Nacional (UTN) - Facultad Regional Resistencia (FRRe)**.

---

## 📌 Descripción del Proyecto
Este simulador permite modelar y observar el comportamiento de:
1. **Planificación de CPU a Corto Plazo**: Algoritmo **SRTF** (*Shortest Remaining Time First*) apropiativo.
2. **Gestión de Memoria Principal**: Esquema de **Particiones Variables (MVT)** con política de asignación **Best-Fit** y coalescencia de huecos libres contiguos.
3. **Control de Grado de Multiprogramación**: Límite máximo de **5 procesos activos simultáneos** (entre Ejecución, Listos y Listos/Suspendidos).

> [!NOTE]
> Todo el simulador fue desarrollado siguiendo de forma estricta el paradigma de **PROGRAMACIÓN ESTRUCTURADA (sin Programación Orientada a Objetos / sin clases)**, mediante funciones y procedimientos modulares.

---

## 🚀 Requisitos y Ejecución
- **Sistema Operativo**: Windows 10 / 11
- **Python**: Versión 3.8 o superior (utiliza la biblioteca estándar `tkinter`, sin dependencias externas `pip`).

### Formas de Ejecución:
1. **Doble clic (Recomendado)**:  
   Ejecutar directamente el archivo `ejecutar_simulador.bat`.
2. **Desde la terminal**:  
   ```bash
   python simulador.py
   ```

---

## 💻 Características de la Interfaz Gráfica
- **Pantalla de Inicio / Bienvenida**: Carga de procesos mediante archivo CSV/TXT o ingreso manual ordenado con validaciones estrictas de formato y cantidad.
- **Reloj del Sistema $T$**: Contador de tiempo destacado para seguimiento visual.
- **Visualizador de Colas**: Monitoreo de procesos en estado *Nuevo*, *Listo*, *Listo y Suspendido*, *En Ejecución* y *Terminado*.
- **Tabla y Mapa de Memoria**: Visualización en tiempo real de particiones, direcciones de inicio, tamaño, asignación y gráfico coloreado.
- **Control de Simulación**:
  - `⏭ Siguiente Ciclo (T + 1)`: Avance paso a paso.
  - `⏮ Ciclo Anterior (T - 1)`: Retroceso en el tiempo (deshacer / undo) ciclo a ciclo.
  - `⏩ Siguiente Evento`: Salto automático a la próxima llegada o finalización de proceso.
  - `🔄 Reiniciar`: Regreso al estado inicial en $T=0$.
- **Informe Estadístico**: Ventana modal con tiempos de retorno ($TR$), tiempos de espera ($TE$), promedios ($TRP$, $TEP$) y rendimiento (*Throughput*).
