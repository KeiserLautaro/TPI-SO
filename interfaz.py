import copy
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from constantes import MAX_PROCESOS, MEMORIA_TOTAL, MAX_MULTIPROGRAMACION
from entrada import leer_archivo, validar_proceso
from informe import texto_informe, suspendidos_bloqueados_por_fragmentacion
from memoria import tabla_particiones, fragmentacion_externa
from planificador import clave_orden_llegada, clave_srtf, numero_de_id
from simulacion import (
    crear_estado, avanzar_instante, avanzar_hasta_evento, simulacion_terminada,
    calcular_estadisticas, grado_multiprogramacion, alertas_del_ultimo_paso,
)

# Carpeta del programa: la del .exe si es el ejecutable generado con PyInstaller
# (ahí __file__ apunta a una carpeta temporal), o la de este archivo si no.
if getattr(sys, "frozen", False):
    CARPETA = os.path.dirname(sys.executable)
else:
    CARPETA = os.path.dirname(os.path.abspath(__file__))
CARPETA_LOTES = os.path.join(CARPETA, "lotes")

COLORES_PROCESOS = ["#74b9ff", "#55efc4", "#ffeaa7", "#fab1a0", "#a29bfe",
                    "#81ecec", "#fd79a8", "#e17055", "#00b894", "#fdcb6e"]

# =============================================================================
# SECCIÓN 1: ESTADO DE LA INTERFAZ
# =============================================================================

procesos_cargados = []   # Procesos de la pantalla de carga (todavía sin simular)
estado = None            # Estado de la simulación en curso (ver simulacion.py)
pila_estados = []        # Copias del estado anteriores, para "Ciclo Anterior"

ventana_principal = None
frame_pantalla_inicio = None
frame_pantalla_simulador = None

entry_manual_id = None
entry_manual_tam = None
entry_manual_ta = None
entry_manual_ti = None
tree_procesos_inicio = None
lbl_contador_procesos = None
lbl_ruta_csv_inicio = None

lbl_badge_reloj_t = None
lbl_alerta = None
lbl_cpu_actual = None
lbl_cpu_restante = None
lbl_cpu_arribo = None
lbl_cpu_tamano = None
lbl_grado = None
tree_listos = None
tree_suspendidos = None
tree_nuevos = None
tree_particiones = None
lbl_fragmentacion = None
canvas_memoria = None
canvas_gantt = None
txt_logs = None
btn_ciclo_anterior = None
btn_siguiente_ciclo = None
btn_siguiente_evento = None


# =============================================================================
# SECCIÓN 2: CONTROL DE LA SIMULACIÓN (BOTONES)
# =============================================================================

def iniciar_estado():
    global estado, pila_estados
    estado = crear_estado(copy.deepcopy(procesos_cargados))
    pila_estados = []
    actualizar_interfaz_grafica()


def ejecutar_paso_a_paso():
    if estado is None or simulacion_terminada(estado):
        return
    pila_estados.append(copy.deepcopy(estado))
    avanzar_instante(estado)
    actualizar_interfaz_grafica()
    if simulacion_terminada(estado):
        mostrar_dialogo_informe_final()


def ejecutar_hasta_siguiente_evento():
    if estado is None or simulacion_terminada(estado):
        return
    pila_estados.append(copy.deepcopy(estado))
    avanzar_hasta_evento(estado)
    actualizar_interfaz_grafica()
    if simulacion_terminada(estado):
        mostrar_dialogo_informe_final()


def retroceder_un_ciclo():
    global estado
    if len(pila_estados) == 0:
        return
    estado = pila_estados.pop()
    actualizar_interfaz_grafica()


def reiniciar_simulacion():
    if len(procesos_cargados) > 0:
        iniciar_estado()


# =============================================================================
# SECCIÓN 3: DIBUJO Y ACTUALIZACIÓN DE LA PANTALLA DE SIMULACIÓN
# =============================================================================

def color_de_proceso(id_proceso):
    return COLORES_PROCESOS[numero_de_id(id_proceso) % len(COLORES_PROCESOS)]


def actualizar_tabla_tree(tree, lista_datos):
    for item in tree.get_children():
        tree.delete(item)
    for fila in lista_datos:
        tree.insert("", tk.END, values=fila)


def filas_de_procesos(procesos, con_restante=True):
    filas = []
    for p in procesos:
        if con_restante:
            filas.append((p["id"], f"{p['tamano']}K", p["arribo"], p["irrupcion"], p["restante"]))
        else:
            filas.append((p["id"], f"{p['tamano']}K", p["arribo"], p["irrupcion"]))
    return filas


def dibujar_canvas_memoria():
    if canvas_memoria is None or estado is None:
        return
    canvas_memoria.delete("all")
    ancho = max(canvas_memoria.winfo_width(), 500)
    alto = max(canvas_memoria.winfo_height(), 45)
    margen_x, margen_y = 10, 6
    ancho_util = ancho - 2 * margen_x

    for fila in tabla_particiones(estado["memoria"]):
        x0 = margen_x + fila["inicio"] / MEMORIA_TOTAL * ancho_util
        x1 = x0 + fila["tamano"] / MEMORIA_TOTAL * ancho_util
        if fila["numero"] == 0:
            color = "#ff7675"
        elif fila["libre"]:
            color = "#dfe6e9"
        else:
            color = color_de_proceso(fila["proceso"])
        canvas_memoria.create_rectangle(x0, margen_y, x1, alto - margen_y, fill=color, outline="#2d3436")
        if x1 - x0 > 30:
            canvas_memoria.create_text((x0 + x1) / 2, alto / 2, text=f"{fila['proceso']}\n{fila['tamano']}K",
                                       font=("Arial", 8, "bold"))


def dibujar_canvas_gantt():
    if canvas_gantt is None or estado is None:
        return
    canvas_gantt.delete("all")
    historial = estado["historial_cpu"]
    if len(historial) == 0:
        canvas_gantt.create_text(10, 20, anchor="w", text="(todavía no se ejecutó ningún instante)",
                                 font=("Arial", 8, "italic"))
        return

    ancho = max(canvas_gantt.winfo_width(), 500)
    margen = 10
    celda = min(28, (ancho - 2 * margen) / len(historial))
    y0, y1 = 6, 30

    inicio = 0
    while inicio < len(historial):
        fin = inicio
        while fin + 1 < len(historial) and historial[fin + 1] == historial[inicio]:
            fin += 1
        id_proceso = historial[inicio]
        x0 = margen + inicio * celda
        x1 = margen + (fin + 1) * celda
        color = "#ffffff" if id_proceso is None else color_de_proceso(id_proceso)
        canvas_gantt.create_rectangle(x0, y0, x1, y1, fill=color, outline="#2d3436")
        if id_proceso is not None and x1 - x0 > 18:
            canvas_gantt.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=id_proceso, font=("Arial", 8, "bold"))
        canvas_gantt.create_text(x0, y1 + 8, text=str(inicio), font=("Arial", 7))
        inicio = fin + 1
    canvas_gantt.create_text(margen + len(historial) * celda, y1 + 8, text=str(len(historial)), font=("Arial", 7))


def actualizar_registro():
    txt_logs.config(state=tk.NORMAL)
    txt_logs.delete("1.0", tk.END)
    for i in range(len(estado["registro"])):
        suceso = estado["registro"][i]
        etiquetas = []
        if i >= estado["inicio_paso"]:
            etiquetas.append("ultimo")
        if suceso["alerta"]:
            etiquetas.append("alerta")
        txt_logs.insert(tk.END, f"[T={suceso['t']}] {suceso['texto']}\n", tuple(etiquetas))
    txt_logs.see(tk.END)
    txt_logs.config(state=tk.DISABLED)


def actualizar_interfaz_grafica():
    if ventana_principal is None or estado is None:
        return

    # Avanzar: no al terminar; retroceder: no en el primer paso
    lbl_badge_reloj_t.config(text=f"T = {estado['t']}")
    estado_botones = tk.DISABLED if simulacion_terminada(estado) else tk.NORMAL
    btn_siguiente_ciclo.config(state=estado_botones)
    btn_siguiente_evento.config(state=estado_botones)
    btn_ciclo_anterior.config(state=tk.NORMAL if len(pila_estados) > 0 else tk.DISABLED)
    alertas = alertas_del_ultimo_paso(estado)
    if len(alertas) > 0:
        textos = []
        for alerta in alertas:
            textos.append(alerta["texto"])
        lbl_alerta.config(text="⚠ " + "  |  ".join(textos), bg="#f1c40f", fg="#2d3436")
    else:
        lbl_alerta.config(text="", bg="#1e272e")

    en_cpu = estado["en_cpu"]
    if en_cpu is not None:
        lbl_cpu_actual.config(text=f"Proceso en CPU: {en_cpu['id']}", fg="#27ae60")
        lbl_cpu_restante.config(text=f"T. Restante: {en_cpu['restante']} u.")
        lbl_cpu_arribo.config(text=f"T. Arribo: {en_cpu['arribo']}")
        lbl_cpu_tamano.config(text=f"Tamaño: {en_cpu['tamano']} KB")
    else:
        lbl_cpu_actual.config(text="Proceso en CPU: LIBRE (Ociosa)", fg="#7f8c8d")
        lbl_cpu_restante.config(text="T. Restante: -")
        lbl_cpu_arribo.config(text="T. Arribo: -")
        lbl_cpu_tamano.config(text="Tamaño: -")
    lbl_grado.config(text=f"Grado de multiprogramación: {grado_multiprogramacion(estado)} / {MAX_MULTIPROGRAMACION}")

    listos = sorted(estado["listos"], key=clave_srtf)
    actualizar_tabla_tree(tree_listos, filas_de_procesos(listos))
    actualizar_tabla_tree(tree_suspendidos, filas_de_procesos(estado["suspendidos"]))
    actualizar_tabla_tree(tree_nuevos, filas_de_procesos(estado["nuevos"], con_restante=False))

    filas = []
    for fila in tabla_particiones(estado["memoria"]):
        filas.append((fila["numero"], f"{fila['inicio']}K", f"{fila['tamano']}K", fila["proceso"],
                      f"{fila['frag_interna']}K"))
    actualizar_tabla_tree(tree_particiones, filas)
    resumen = fragmentacion_externa(estado["memoria"])
    texto_frag = (f"Libre: {resumen['total_libre']}K en {resumen['cantidad_huecos']} hueco(s) | "
                  f"Mayor hueco: {resumen['mayor_hueco']}K")
    bloqueados = suspendidos_bloqueados_por_fragmentacion(estado)
    if len(bloqueados) > 0:
        texto_frag += f"\nFragmentación externa: a {', '.join(bloqueados)} le alcanza la memoria libre total, pero no entra en ningún hueco."
        lbl_fragmentacion.config(text=texto_frag, fg="#c0392b")
    else:
        lbl_fragmentacion.config(text=texto_frag, fg="#2c3e50")
    dibujar_canvas_memoria()
    dibujar_canvas_gantt()

    actualizar_registro()


def exportar_informe():
    ruta = filedialog.asksaveasfilename(
        title="Guardar informe", defaultextension=".txt", initialfile="informe.txt",
        filetypes=[("Texto", "*.txt")],
    )
    if ruta:
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write(texto_informe(estado))
        messagebox.showinfo("Informe", f"Informe guardado en:\n{ruta}")


def mostrar_dialogo_informe_final():
    if estado is None:
        return
    stats = calcular_estadisticas(estado)

    modal = tk.Toplevel(ventana_principal)
    modal.title("Informe Estadístico de la Simulación")
    modal.geometry("680x480")
    modal.transient(ventana_principal)
    modal.grab_set()

    titulo = "INFORME ESTADÍSTICO FINAL" if simulacion_terminada(estado) else f"INFORME PARCIAL (T = {estado['t']})"
    tk.Label(modal, text=titulo, font=("Arial", 12, "bold"), pady=10).pack()

    frame_t = tk.Frame(modal, padx=10, pady=5)
    frame_t.pack(fill=tk.BOTH, expand=True)

    cols = ("ID", "Tamaño", "TA", "TI", "T_Fin", "TR (Retorno)", "TE (Espera)")
    tr_mod = ttk.Treeview(frame_t, columns=cols, show='headings', height=8)
    for c in cols:
        tr_mod.heading(c, text=c)
        tr_mod.column(c, width=85, anchor='center')
    tr_mod.pack(fill=tk.BOTH, expand=True)
    for d in stats["detalle"]:
        tr_mod.insert("", tk.END, values=(d["id"], f"{d['tamano']}K", d["arribo"], d["irrupcion"],
                                          d["fin"], d["retorno"], d["espera"]))

    frame_ind = tk.LabelFrame(modal, text="Indicadores Globales", padx=12, pady=10, font=("Arial", 10, "bold"))
    frame_ind.pack(fill=tk.X, padx=15, pady=10)
    txt_res = (
        f"• Procesos terminados: {stats['cantidad']} de {len(estado['procesos'])}\n"
        f"• Tiempo total: {stats['tiempo_total']} unidades de tiempo\n"
        f"• Tiempo de Retorno Promedio (TRP): {stats['retorno_promedio']:.2f} unidades\n"
        f"• Tiempo de Espera Promedio (TEP): {stats['espera_promedio']:.2f} unidades\n"
        f"• Rendimiento: {stats['cantidad']} / {stats['tiempo_total']} = "
        f"{stats['rendimiento']:.4f} procesos por unidad de tiempo"
    )
    tk.Label(frame_ind, text=txt_res, justify=tk.LEFT, font=("Arial", 10)).pack(anchor="w")

    frame_botones = tk.Frame(modal)
    frame_botones.pack(pady=8)
    tk.Button(frame_botones, text="Exportar a TXT", bg="#8e44ad", fg="white", font=("Arial", 10, "bold"),
              padx=15, pady=4, cursor="hand2", command=exportar_informe).pack(side=tk.LEFT, padx=5)
    tk.Button(frame_botones, text="Cerrar", bg="#34495e", fg="white", font=("Arial", 10, "bold"),
              padx=15, pady=4, cursor="hand2", command=modal.destroy).pack(side=tk.LEFT, padx=5)


# =============================================================================
# SECCIÓN 4: CONTROLADORES DE LA PANTALLA DE INICIO
# =============================================================================

def refrescar_tabla_procesos_inicio():
    procesos_cargados.sort(key=clave_orden_llegada)
    filas = []
    for p in procesos_cargados:
        filas.append((p["id"], f"{p['tamano']} KB", p["arribo"], p["irrupcion"]))
    actualizar_tabla_tree(tree_procesos_inicio, filas)
    lbl_contador_procesos.config(text=f"Procesos cargados: {len(procesos_cargados)} / {MAX_PROCESOS}")


def cargar_archivo(ruta):
    global procesos_cargados
    procesos, errores = leer_archivo(ruta)
    if len(errores) > 0:
        lista_errores = "\n".join("• " + e for e in errores)
        if len(procesos) == 0:
            messagebox.showerror("Archivo con errores", f"No se pudo cargar ningún proceso:\n\n{lista_errores}")
            return False
        ids = ", ".join(p["id"] for p in procesos)
        seguir = messagebox.askyesno(
            "Archivo con errores",
            f"Se encontraron problemas:\n\n{lista_errores}\n\n"
            f"¿Continuar con los {len(procesos)} procesos válidos?\n({ids})",
        )
        if not seguir:
            return False
    procesos_cargados = procesos
    lbl_ruta_csv_inicio.config(text=f"Archivo cargado: {os.path.basename(ruta)}", fg="#27ae60")
    refrescar_tabla_procesos_inicio()
    return True


def accion_cargar_csv_inicio():
    carpeta = CARPETA_LOTES if os.path.isdir(CARPETA_LOTES) else CARPETA
    ruta = filedialog.askopenfilename(
        title="Seleccionar archivo de procesos (CSV)",
        initialdir=carpeta,
        filetypes=[("Archivos CSV", "*.csv")],
    )
    if ruta:
        cargar_archivo(ruta)


def accion_agregar_proceso_manual():
    if len(procesos_cargados) >= MAX_PROCESOS:
        messagebox.showerror("Cantidad de procesos superada",
                             f"Ya se cargó el máximo de {MAX_PROCESOS} procesos.")
        return

    proceso, error = validar_proceso(entry_manual_id.get(), entry_manual_tam.get(),
                                     entry_manual_ta.get(), entry_manual_ti.get())
    if proceso is None:
        messagebox.showerror("Proceso incorrecto", error)
        return
    for p in procesos_cargados:
        if p["id"] == proceso["id"]:
            messagebox.showerror("Proceso incorrecto", f"Ya existe un proceso con el Id '{proceso['id']}'.")
            return

    procesos_cargados.append(proceso)
    for entry in (entry_manual_id, entry_manual_tam, entry_manual_ta, entry_manual_ti):
        entry.delete(0, tk.END)
    entry_manual_id.focus_set()
    refrescar_tabla_procesos_inicio()


def accion_eliminar_proceso_seleccionado():
    seleccion = tree_procesos_inicio.selection()
    if not seleccion:
        messagebox.showinfo("Atención", "Seleccione un proceso de la tabla para eliminarlo.")
        return
    id_proceso = str(tree_procesos_inicio.item(seleccion[0])["values"][0])
    for i in range(len(procesos_cargados)):
        if procesos_cargados[i]["id"] == id_proceso:
            procesos_cargados.pop(i)
            break
    refrescar_tabla_procesos_inicio()


def accion_limpiar_todos_los_procesos():
    procesos_cargados.clear()
    lbl_ruta_csv_inicio.config(text="Ningún archivo cargado.", fg="#7f8c8d")
    refrescar_tabla_procesos_inicio()


def iniciar_simulacion_desde_inicio():
    if len(procesos_cargados) == 0:
        messagebox.showwarning("Sin procesos", "Debe cargar al menos 1 proceso (archivo o manual).")
        return
    frame_pantalla_inicio.pack_forget()
    frame_pantalla_simulador.pack(fill=tk.BOTH, expand=True)
    ventana_principal.update_idletasks()   # para que los gráficos ya tengan su tamaño real
    iniciar_estado()


def volver_a_pantalla_inicio():
    frame_pantalla_simulador.pack_forget()
    frame_pantalla_inicio.pack(fill=tk.BOTH, expand=True)
    refrescar_tabla_procesos_inicio()


# =============================================================================
# SECCIÓN 5: CONSTRUCCIÓN VISUAL DE LAS PANTALLAS
# =============================================================================

def crear_boton(padre, texto, color, color_activo, comando, tamano_letra=9):
    return tk.Button(
        padre, text=texto, font=("Arial", tamano_letra, "bold"), bg=color, fg="white",
        activebackground=color_activo, activeforeground="white", relief=tk.RAISED, bd=2,
        cursor="hand2", padx=10, pady=5, command=comando,
    )


def crear_tabla(padre, columnas, alto, ancho_columna):
    tree = ttk.Treeview(padre, columns=columnas, show='headings', height=alto)
    for c in columnas:
        tree.heading(c, text=c)
        tree.column(c, width=ancho_columna, anchor='center')
    tree.pack(fill=tk.BOTH, expand=True)
    return tree


def construir_pantalla_inicio(parent):
    global frame_pantalla_inicio, entry_manual_id, entry_manual_tam, entry_manual_ta, entry_manual_ti
    global tree_procesos_inicio, lbl_contador_procesos, lbl_ruta_csv_inicio

    frame_pantalla_inicio = tk.Frame(parent, bg="#f5f6fa")

    banner = tk.Frame(frame_pantalla_inicio, bg="#2c3e50", padx=20, pady=16)
    banner.pack(fill=tk.X)
    tk.Label(banner, text="SISTEMAS OPERATIVOS - UTN FRRe", font=("Arial", 11, "bold"),
             fg="#bdc3c7", bg="#2c3e50").pack()
    tk.Label(banner, text="Simulador de Asignación de Memoria y Planificación de CPU",
             font=("Arial", 16, "bold"), fg="#ffffff", bg="#2c3e50", pady=4).pack()
    tk.Label(banner, text="Planificador SRTF (Apropiativo) • Memoria con Particiones Variables (MVT Best-Fit)",
             font=("Arial", 10), fg="#f1c40f", bg="#2c3e50").pack()

    # Barra inferior con el botón de iniciar (se empaqueta antes para que siempre se vea)
    frame_pie_inicio = tk.Frame(frame_pantalla_inicio, bg="#ecf0f1", padx=20, pady=12, bd=1, relief=tk.RIDGE)
    frame_pie_inicio.pack(fill=tk.X, side=tk.BOTTOM)
    crear_boton(frame_pie_inicio, "🚀 INICIAR SIMULACIÓN CON ESTOS PROCESOS", "#27ae60", "#219a52",
                iniciar_simulacion_desde_inicio, tamano_letra=12).pack()

    cuerpo = tk.Frame(frame_pantalla_inicio, bg="#f5f6fa", padx=15, pady=12)
    cuerpo.pack(fill=tk.BOTH, expand=True)

    col_izq = tk.Frame(cuerpo, bg="#f5f6fa", width=420)
    col_izq.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))

    lf_csv = tk.LabelFrame(col_izq, text="Opción A: Cargar desde Archivo CSV",
                           font=("Arial", 10, "bold"), padx=12, pady=10, bg="white")
    lf_csv.pack(fill=tk.X, pady=(0, 10))
    crear_boton(lf_csv, "📁 Seleccionar Archivo CSV", "#3498db", "#2980b9",
                accion_cargar_csv_inicio).pack(fill=tk.X)
    lbl_ruta_csv_inicio = tk.Label(lf_csv, text="Ningún archivo cargado.", font=("Arial", 8, "italic"),
                                   bg="white", fg="#7f8c8d")
    lbl_ruta_csv_inicio.pack(anchor="w", pady=(5, 0))

    lf_manual = tk.LabelFrame(col_izq, text="Opción B: Carga Manual de Proceso",
                              font=("Arial", 10, "bold"), padx=12, pady=10, bg="white")
    lf_manual.pack(fill=tk.BOTH, expand=True)
    grid_form = tk.Frame(lf_manual, bg="white")
    grid_form.pack(fill=tk.X, pady=4)

    etiquetas = ["ID Proceso (ej: P1):", "Tamaño (KB, máx 450):", "Tiempo Arribo (TA >= 0):",
                 "Tiempo Irrupción (TI > 0):"]
    entradas = []
    for fila in range(4):
        tk.Label(grid_form, text=etiquetas[fila], font=("Arial", 9), bg="white").grid(
            row=fila, column=0, sticky="w", pady=4)
        entrada = ttk.Entry(grid_form, width=15)
        entrada.grid(row=fila, column=1, sticky="ew", pady=4, padx=5)
        entradas.append(entrada)
    entry_manual_id, entry_manual_tam, entry_manual_ta, entry_manual_ti = entradas

    crear_boton(lf_manual, "➕ Agregar Proceso a la Lista", "#27ae60", "#219a52",
                accion_agregar_proceso_manual).pack(fill=tk.X, pady=(10, 4))

    col_der = tk.LabelFrame(cuerpo, text="Procesos Cargados para la Simulación",
                            font=("Arial", 10, "bold"), padx=12, pady=10, bg="white")
    col_der.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    frame_acciones_tabla = tk.Frame(col_der, bg="white", pady=8)
    frame_acciones_tabla.pack(fill=tk.X, side=tk.BOTTOM)
    tree_procesos_inicio = crear_tabla(col_der, ("ID", "Tamaño", "Tiempo Arribo (TA)", "Tiempo Irrupción (TI)"),
                                       10, 110)

    lbl_contador_procesos = tk.Label(frame_acciones_tabla, text=f"Procesos cargados: 0 / {MAX_PROCESOS}",
                                     font=("Arial", 10, "bold"), bg="white", fg="#2c3e50")
    lbl_contador_procesos.pack(side=tk.LEFT)
    tk.Button(frame_acciones_tabla, text="Limpiar Todo", font=("Arial", 8), bg="#e74c3c", fg="white",
              cursor="hand2", command=accion_limpiar_todos_los_procesos).pack(side=tk.RIGHT, padx=4)
    tk.Button(frame_acciones_tabla, text="Eliminar Seleccionado", font=("Arial", 8), bg="#95a5a6", fg="white",
              cursor="hand2", command=accion_eliminar_proceso_seleccionado).pack(side=tk.RIGHT, padx=4)


def construir_pantalla_simulador(parent):
    global frame_pantalla_simulador, lbl_badge_reloj_t, lbl_alerta, lbl_grado
    global lbl_cpu_actual, lbl_cpu_restante, lbl_cpu_arribo, lbl_cpu_tamano
    global tree_listos, tree_suspendidos, tree_nuevos, tree_particiones, lbl_fragmentacion
    global canvas_memoria, canvas_gantt, txt_logs
    global btn_ciclo_anterior, btn_siguiente_ciclo, btn_siguiente_evento

    frame_pantalla_simulador = tk.Frame(parent, bg="#f5f6fa")

    # ------------------ ENCABEZADO CON RELOJ T Y ALERTA ------------------
    frame_top = tk.Frame(frame_pantalla_simulador, bg="#1e272e", padx=16, pady=8)
    frame_top.pack(fill=tk.X)

    frame_titulos = tk.Frame(frame_top, bg="#1e272e")
    frame_titulos.pack(side=tk.LEFT, fill=tk.X, expand=True)
    tk.Label(frame_titulos, text="SIMULADOR DE PLANIFICACIÓN CPU (SRTF) Y MEMORIA (MVT BEST-FIT)",
             font=("Arial", 11, "bold"), fg="#ffffff", bg="#1e272e").pack(anchor="w")
    tk.Label(frame_titulos, text="UTN FRRe - Sistemas Operativos | 550K (100K SO + 450K Usuario) | Máx 5 activos",
             font=("Arial", 8), fg="#95a5a6", bg="#1e272e").pack(anchor="w")
    lbl_alerta = tk.Label(frame_titulos, text="", font=("Arial", 9, "bold"), bg="#1e272e",
                          anchor="w", justify=tk.LEFT, wraplength=850)
    lbl_alerta.pack(anchor="w", fill=tk.X, pady=(4, 0))

    frame_badge_t = tk.Frame(frame_top, bg="#000000", highlightbackground="#f39c12",
                             highlightcolor="#f39c12", highlightthickness=2, padx=14, pady=3)
    frame_badge_t.pack(side=tk.RIGHT)
    tk.Label(frame_badge_t, text="TIEMPO DEL SISTEMA", font=("Arial", 7, "bold"),
             fg="#f1c40f", bg="#000000").pack()
    lbl_badge_reloj_t = tk.Label(frame_badge_t, text="T = 0", font=("Consolas", 18, "bold"),
                                 fg="#00d2d3", bg="#000000")
    lbl_badge_reloj_t.pack()

    # ------------------ BARRA INFERIOR DE BOTONES ------------------
    # (se empaqueta antes que el centro para que siempre quede visible)
    frame_botones = tk.Frame(frame_pantalla_simulador, bg="#2f3640", padx=10, pady=8, bd=2, relief=tk.RIDGE)
    frame_botones.pack(fill=tk.X, side=tk.BOTTOM)
    btn_ciclo_anterior = crear_boton(frame_botones, "⏮ Ciclo Anterior", "#27ae60", "#219a52",
                                     retroceder_un_ciclo, 10)
    btn_ciclo_anterior.pack(side=tk.LEFT, padx=5)
    btn_siguiente_ciclo = crear_boton(frame_botones, "⏭ Siguiente Ciclo (T + 1)", "#27ae60", "#219a52",
                                      ejecutar_paso_a_paso, 10)
    btn_siguiente_ciclo.pack(side=tk.LEFT, padx=5)
    btn_siguiente_evento = crear_boton(frame_botones, "⏩ Siguiente Evento (Arribo/Fin)", "#2980b9", "#1f618d",
                                       ejecutar_hasta_siguiente_evento)
    btn_siguiente_evento.pack(side=tk.LEFT, padx=5)
    crear_boton(frame_botones, "🔄 Reiniciar (T=0)", "#e67e22", "#d35400", reiniciar_simulacion).pack(side=tk.LEFT, padx=5)
    crear_boton(frame_botones, "📊 Informe Estadístico", "#8e44ad", "#71368a", mostrar_dialogo_informe_final).pack(side=tk.LEFT, padx=5)
    crear_boton(frame_botones, "🏠 Volver a Inicio / Carga", "#7f8c8d", "#636e72", volver_a_pantalla_inicio).pack(side=tk.RIGHT, padx=5)

    # ------------------ PANELES CENTRALES ------------------
    paned_central = tk.PanedWindow(frame_pantalla_simulador, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
    paned_central.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    # --- Izquierda: CPU y colas ---
    frame_izq = tk.Frame(paned_central, bg="#f5f6fa")
    paned_central.add(frame_izq, minsize=420)

    lf_cpu = tk.LabelFrame(frame_izq, text="Estado del Procesador (CPU)", font=("Arial", 9, "bold"),
                           padx=8, pady=4, bg="white")
    lf_cpu.pack(fill=tk.X, pady=2)
    lbl_cpu_actual = tk.Label(lf_cpu, text="Proceso en CPU: LIBRE", font=("Arial", 11, "bold"),
                              fg="#7f8c8d", bg="white")
    lbl_cpu_actual.pack(anchor="w")
    frame_cpu_detalles = tk.Frame(lf_cpu, bg="white")
    frame_cpu_detalles.pack(fill=tk.X, pady=2)
    lbl_cpu_restante = tk.Label(frame_cpu_detalles, text="T. Restante: -", font=("Arial", 9), bg="white")
    lbl_cpu_restante.pack(side=tk.LEFT, padx=6)
    lbl_cpu_arribo = tk.Label(frame_cpu_detalles, text="T. Arribo: -", font=("Arial", 9), bg="white")
    lbl_cpu_arribo.pack(side=tk.LEFT, padx=6)
    lbl_cpu_tamano = tk.Label(frame_cpu_detalles, text="Tamaño: -", font=("Arial", 9), bg="white")
    lbl_cpu_tamano.pack(side=tk.LEFT, padx=6)
    lbl_grado = tk.Label(lf_cpu, text="", font=("Arial", 9), bg="white", fg="#2c3e50")
    lbl_grado.pack(anchor="w", padx=6)

    cols_proc = ("ID", "Tamaño", "Arribo", "TI", "T. Restante")
    lf_listos = tk.LabelFrame(frame_izq, text="Cola de Listos (en memoria, esperando CPU)",
                              font=("Arial", 9, "bold"), padx=4, pady=2, bg="white")
    lf_listos.pack(fill=tk.BOTH, expand=True, pady=2)
    tree_listos = crear_tabla(lf_listos, cols_proc, 3, 70)

    lf_susp = tk.LabelFrame(frame_izq, text="Cola de Listos y Suspendidos (admitidos, sin memoria)",
                            font=("Arial", 9, "bold"), padx=4, pady=2, bg="white")
    lf_susp.pack(fill=tk.BOTH, expand=True, pady=2)
    tree_suspendidos = crear_tabla(lf_susp, cols_proc, 3, 70)

    lf_nuevos = tk.LabelFrame(frame_izq, text="Cola de Nuevos (esperando cupo de multiprogramación)",
                              font=("Arial", 9, "bold"), padx=4, pady=2, bg="white")
    lf_nuevos.pack(fill=tk.BOTH, expand=True, pady=2)
    tree_nuevos = crear_tabla(lf_nuevos, ("ID", "Tamaño", "Arribo", "TI"), 2, 80)

    # --- Derecha: memoria, Gantt y sucesos ---
    frame_der = tk.Frame(paned_central, bg="#f5f6fa")
    paned_central.add(frame_der, minsize=480)

    lf_memoria = tk.LabelFrame(frame_der, text="Tabla de Particiones MVT (100K SO + 450K Usuario)",
                               font=("Arial", 9, "bold"), padx=4, pady=2, bg="white")
    lf_memoria.pack(fill=tk.BOTH, expand=True, pady=2)
    tree_particiones = crear_tabla(lf_memoria, ("Partición", "Dir. Comienzo", "Tamaño", "Proceso", "Frag. Interna"),
                                   5, 90)
    lbl_fragmentacion = tk.Label(lf_memoria, text="", font=("Arial", 8), bg="white", justify=tk.LEFT,
                                 anchor="w", wraplength=460)
    lbl_fragmentacion.pack(anchor="w", fill=tk.X)
    canvas_memoria = tk.Canvas(lf_memoria, height=45, bg="#f9f9f9", bd=1, relief=tk.SUNKEN)
    canvas_memoria.pack(fill=tk.X, pady=2)
    canvas_memoria.bind("<Configure>", lambda evento: dibujar_canvas_memoria())

    lf_gantt = tk.LabelFrame(frame_der, text="Diagrama de Gantt (uso de la CPU)", font=("Arial", 9, "bold"),
                             padx=4, pady=2, bg="white")
    lf_gantt.pack(fill=tk.X, pady=2)
    canvas_gantt = tk.Canvas(lf_gantt, height=48, bg="#f9f9f9", bd=1, relief=tk.SUNKEN)
    canvas_gantt.pack(fill=tk.X, pady=2)
    canvas_gantt.bind("<Configure>", lambda evento: dibujar_canvas_gantt())

    lf_logs = tk.LabelFrame(frame_der, text="Registro de Sucesos (en negrita: los del último paso)",
                            font=("Arial", 9, "bold"), padx=4, pady=2, bg="white")
    lf_logs.pack(fill=tk.BOTH, expand=True, pady=2)
    scroll_logs = ttk.Scrollbar(lf_logs)
    scroll_logs.pack(side=tk.RIGHT, fill=tk.Y)
    txt_logs = tk.Text(lf_logs, height=5, font=("Consolas", 8), yscrollcommand=scroll_logs.set)
    txt_logs.pack(fill=tk.BOTH, expand=True)
    txt_logs.tag_configure("ultimo", font=("Consolas", 8, "bold"))
    txt_logs.tag_configure("alerta", foreground="#c0392b")
    scroll_logs.config(command=txt_logs.yview)


# =============================================================================
# SECCIÓN 6: PUNTO DE ENTRADA
# =============================================================================

def main():
    global ventana_principal

    ventana_principal = tk.Tk()
    ventana_principal.title("Simulador de Memoria y CPU - Sistemas Operativos (UTN FRRe) - Equipo 9")
    ventana_principal.geometry("1120x820")
    ventana_principal.minsize(980, 720)

    contenedor_raiz = tk.Frame(ventana_principal)
    contenedor_raiz.pack(fill=tk.BOTH, expand=True)

    construir_pantalla_inicio(contenedor_raiz)
    construir_pantalla_simulador(contenedor_raiz)
    frame_pantalla_inicio.pack(fill=tk.BOTH, expand=True)

    ventana_principal.bind("<Right>", lambda evento: ejecutar_paso_a_paso() if frame_pantalla_simulador.winfo_ismapped() else None)
    ventana_principal.bind("<Left>", lambda evento: retroceder_un_ciclo() if frame_pantalla_simulador.winfo_ismapped() else None)

    ventana_principal.mainloop()


if __name__ == "__main__":
    main()
