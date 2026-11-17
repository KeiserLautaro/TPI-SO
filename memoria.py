from constantes import MEMORIA_SO, MEMORIA_USUARIO


def crear_memoria():
    return [{"inicio": MEMORIA_SO, "tamano": MEMORIA_USUARIO, "proceso": None}]


def buscar_hueco_best_fit(memoria, tamano):
    mejor = -1
    for i in range(len(memoria)):
        particion = memoria[i]
        if particion["proceso"] is None and particion["tamano"] >= tamano:
            if mejor == -1 or particion["tamano"] < memoria[mejor]["tamano"]:
                mejor = i
    return mejor


def asignar_memoria(memoria, id_proceso, tamano):
    i = buscar_hueco_best_fit(memoria, tamano)
    if i == -1:
        return False

    hueco = memoria[i]
    sobrante = hueco["tamano"] - tamano
    if sobrante > 0:
        nuevo_hueco = {"inicio": hueco["inicio"] + tamano, "tamano": sobrante, "proceso": None}
        memoria.insert(i + 1, nuevo_hueco)
    hueco["tamano"] = tamano
    hueco["proceso"] = id_proceso
    return True


def liberar_memoria(memoria, id_proceso):
    for particion in memoria:
        if particion["proceso"] == id_proceso:
            particion["proceso"] = None
            break

    # Fusionar huecos libres contiguos
    i = 0
    while i < len(memoria) - 1:
        actual = memoria[i]
        siguiente = memoria[i + 1]
        if actual["proceso"] is None and siguiente["proceso"] is None:
            actual["tamano"] += siguiente["tamano"]
            memoria.pop(i + 1)
        else:
            i += 1


def tabla_particiones(memoria):
    filas = [{
        "numero": 0, "inicio": 0, "tamano": MEMORIA_SO,
        "proceso": "S.O.", "frag_interna": 0, "libre": False,
    }]
    numero = 1
    for particion in memoria:
        filas.append({
            "numero": numero,
            "inicio": particion["inicio"],
            "tamano": particion["tamano"],
            "proceso": particion["proceso"] if particion["proceso"] else "Libre",
            "frag_interna": 0,
            "libre": particion["proceso"] is None,
        })
        numero += 1
    return filas


def fragmentacion_externa(memoria):
    total = 0
    cantidad = 0
    mayor = 0
    for particion in memoria:
        if particion["proceso"] is None:
            total += particion["tamano"]
            cantidad += 1
            if particion["tamano"] > mayor:
                mayor = particion["tamano"]
    return {"total_libre": total, "cantidad_huecos": cantidad, "mayor_hueco": mayor}
