from memoria import (crear_memoria, asignar_memoria, liberar_memoria, buscar_hueco_best_fit,
                     tabla_particiones, fragmentacion_externa)


def test_corte_exacto_y_sobrante():
    m = crear_memoria()
    assert asignar_memoria(m, "P1", 120)
    assert m == [{"inicio": 100, "tamano": 120, "proceso": "P1"},
                 {"inicio": 220, "tamano": 330, "proceso": None}]


def test_best_fit_elige_el_hueco_mas_chico():
    m = crear_memoria()
    for id_p, tam in [("A", 100), ("B", 50), ("C", 60), ("D", 100)]:
        asignar_memoria(m, id_p, tam)
    liberar_memoria(m, "A")   # hueco de 100K en la dirección 100
    liberar_memoria(m, "C")   # hueco de 60K en la dirección 250
    # Libres: 100K (dir 100), 60K (dir 250), 140K (dir 410). Para 55K el mejor es el de 60K.
    i = buscar_hueco_best_fit(m, 55)
    assert m[i]["inicio"] == 250


def test_best_fit_empate_menor_direccion():
    m = crear_memoria()
    for id_p, tam in [("A", 50), ("B", 10), ("C", 50), ("D", 340)]:
        asignar_memoria(m, id_p, tam)
    liberar_memoria(m, "A")
    liberar_memoria(m, "C")
    assert m[buscar_hueco_best_fit(m, 50)]["inicio"] == 100


def test_no_entra():
    m = crear_memoria()
    asignar_memoria(m, "A", 400)
    assert not asignar_memoria(m, "B", 51)


def test_liberar_fusiona_vecinos():
    m = crear_memoria()
    for id_p in ["A", "B", "C"]:
        asignar_memoria(m, id_p, 100)
    liberar_memoria(m, "A")
    liberar_memoria(m, "C")   # se une con el hueco final
    liberar_memoria(m, "B")   # se une con los dos lados
    assert m == crear_memoria()


def test_tabla_y_fragmentacion_externa():
    m = crear_memoria()
    for id_p in ["A", "B", "C"]:
        asignar_memoria(m, id_p, 100)
    liberar_memoria(m, "B")
    filas = tabla_particiones(m)
    assert filas[0]["proceso"] == "S.O." and filas[0]["tamano"] == 100
    assert [f["numero"] for f in filas] == [0, 1, 2, 3, 4]
    assert all(f["frag_interna"] == 0 for f in filas)
    assert fragmentacion_externa(m) == {"total_libre": 250, "cantidad_huecos": 2, "mayor_hueco": 150}
