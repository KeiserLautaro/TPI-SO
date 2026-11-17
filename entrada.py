import csv

from constantes import MEMORIA_USUARIO, MAX_PROCESOS
from simulacion import crear_proceso

COLUMNAS = ["id", "tamano", "arribo", "irrupcion"]

# Nombres aceptados en el encabezado (ya en minúscula, sin tildes ni "(k)")
ALIAS_COLUMNAS = {
    "id": "id", "proceso": "id", "id_proceso": "id", "pid": "id",
    "tamano": "tamano", "tamanio": "tamano", "tam": "tamano", "memoria": "tamano",
    "arribo": "arribo", "ta": "arribo", "tiempo_arribo": "arribo", "llegada": "arribo",
    "irrupcion": "irrupcion", "ti": "irrupcion", "tiempo_irrupcion": "irrupcion", "rafaga": "irrupcion",
}


def normalizar_id(texto):
    id_limpio = texto.strip().upper()
    if id_limpio.isdigit():
        id_limpio = "P" + str(int(id_limpio))
    return id_limpio


def validar_proceso(texto_id, texto_tamano, texto_arribo, texto_irrupcion):
    id_proceso = normalizar_id(str(texto_id))
    if id_proceso == "":
        return None, "el Id no puede estar vacío."

    try:
        tamano = int(str(texto_tamano).strip())
        arribo = int(str(texto_arribo).strip())
        irrupcion = int(str(texto_irrupcion).strip())
    except ValueError:
        return None, f"{id_proceso}: tamaño, arribo e irrupción deben ser números enteros."

    if tamano <= 0:
        return None, f"{id_proceso}: el tamaño debe ser mayor que 0K."
    if tamano > MEMORIA_USUARIO:
        return None, (f"{id_proceso}: ocupa {tamano}K y nunca podría entrar en memoria "
                      f"(el área de usuario es de {MEMORIA_USUARIO}K).")
    if arribo < 0:
        return None, f"{id_proceso}: el tiempo de arribo debe ser mayor o igual a 0."
    if irrupcion <= 0:
        return None, f"{id_proceso}: el tiempo de irrupción debe ser mayor que 0."

    return crear_proceso(id_proceso, tamano, arribo, irrupcion), ""


def validar_filas(filas):
    procesos = []
    errores = []
    ids_vistos = []

    for numero, campos in filas:
        if len(campos) != 4:
            errores.append(f"Línea {numero}: se esperaban 4 valores y hay {len(campos)}.")
            continue
        proceso, error = validar_proceso(campos[0], campos[1], campos[2], campos[3])
        if proceso is None:
            errores.append(f"Línea {numero}: {error}")
            continue
        if proceso["id"] in ids_vistos:
            errores.append(f"Línea {numero}: el Id {proceso['id']} está repetido.")
            continue
        ids_vistos.append(proceso["id"])
        procesos.append(proceso)

    if len(procesos) > MAX_PROCESOS:
        descartados = []
        for proceso in procesos[MAX_PROCESOS:]:
            descartados.append(proceso["id"])
        errores.append(
            f"Hay {len(procesos)} procesos válidos y el máximo es {MAX_PROCESOS}: "
            f"se toman los {MAX_PROCESOS} primeros y se descartan {', '.join(descartados)}."
        )
        procesos = procesos[:MAX_PROCESOS]

    return procesos, errores


def normalizar_encabezado(texto):
    texto = texto.strip().lower()
    for viejo, nuevo in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]:
        texto = texto.replace(viejo, nuevo)
    texto = texto.replace("(kb)", "").replace("(k)", "").strip()
    texto = texto.replace(" ", "_")
    return texto


def separar_linea(linea):
    for separador in [";", ",", "\t"]:
        if separador in linea:
            return next(csv.reader([linea], delimiter=separador))
    return linea.split()


def es_encabezado(campos):
    for campo in campos[1:]:
        if not campo.strip().lstrip("-").isdigit():
            return True
    return False


def leer_texto_archivo(ruta):
    try:
        with open(ruta, encoding="utf-8-sig") as archivo:
            return archivo.read()
    except UnicodeDecodeError:
        with open(ruta, encoding="latin-1") as archivo:
            return archivo.read()


def leer_archivo(ruta):
    if not str(ruta).lower().endswith(".csv"):
        return [], ["Solo se aceptan archivos .csv."]
    try:
        texto = leer_texto_archivo(ruta)
    except OSError as error:
        return [], [f"No se pudo abrir el archivo: {error}"]

    lineas = []
    numero = 0
    for linea in texto.splitlines():
        numero += 1
        if linea.strip() != "":
            # "Tamaño (K)" se escribe con espacio: se quita antes de separar
            linea = linea.replace("(K)", "").replace("(k)", "")
            lineas.append((numero, separar_linea(linea)))

    if len(lineas) == 0:
        return [], ["El archivo está vacío."]

    # Orden de las columnas: según el encabezado, o el orden por defecto
    orden = [0, 1, 2, 3]
    if es_encabezado(lineas[0][1]):
        nombres = []
        for campo in lineas[0][1]:
            nombre = normalizar_encabezado(campo)
            nombres.append(ALIAS_COLUMNAS.get(nombre, nombre))
        faltantes = []
        for columna in COLUMNAS:
            if columna not in nombres:
                faltantes.append(columna)
        if len(faltantes) > 0 or len(nombres) != 4:
            return [], [
                f"Encabezado inválido: '{' '.join(lineas[0][1])}'. Se esperaban las columnas "
                f"id, tamaño, arribo e irrupción (en cualquier orden)."
            ]
        orden = []
        for columna in COLUMNAS:
            orden.append(nombres.index(columna))
        lineas = lineas[1:]

    filas = []
    for numero, campos in lineas:
        if len(campos) == 4:
            campos = [campos[orden[0]], campos[orden[1]], campos[orden[2]], campos[orden[3]]]
        filas.append((numero, campos))

    procesos, errores = validar_filas(filas)
    if len(procesos) == 0 and len(errores) == 0:
        errores.append("El archivo no tiene procesos.")
    return procesos, errores
