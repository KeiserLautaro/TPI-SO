# -*- coding: utf-8 -*-
from entrada import leer_archivo, validar_proceso, normalizar_id


def escribir(tmp_path, texto, encoding="utf-8"):
    ruta = tmp_path / "procesos.csv"
    ruta.write_text(texto, encoding=encoding)
    return ruta


def test_sin_encabezado_orden_por_defecto(tmp_path):
    procesos, errores = leer_archivo(escribir(tmp_path, "P1,120,0,8\nP2,250,2,4\n"))
    assert errores == []
    assert (procesos[0]["tamano"], procesos[0]["arribo"], procesos[0]["irrupcion"]) == (120, 0, 8)


def test_encabezado_como_el_pdf_separado_por_espacios(tmp_path):
    texto = "Proceso TA TI Tamaño (K)\nP1 3 2 120\nP2 10 4 130\n"
    procesos, errores = leer_archivo(escribir(tmp_path, texto))
    assert errores == []
    assert (procesos[0]["tamano"], procesos[0]["arribo"], procesos[0]["irrupcion"]) == (120, 3, 2)


def test_punto_y_coma_y_latin1(tmp_path):
    texto = "id;tamaño;arribo;irrupción\n1;100;0;5\n"
    procesos, errores = leer_archivo(escribir(tmp_path, texto, encoding="latin-1"))
    assert errores == []
    assert procesos[0]["id"] == "P1"


def test_errores_no_frenan_a_los_validos(tmp_path):
    texto = ("id,tamano,arribo,irrupcion\n"
             "P1,100,0,5\nP2,abc,0,5\nP1,50,1,2\nP3,0,1,1\nP4,50,-1,2\nP5,50,1,0\nP6,50,1\nP7,50,2,3\n")
    procesos, errores = leer_archivo(escribir(tmp_path, texto))
    assert [p["id"] for p in procesos] == ["P1", "P7"]
    assert len(errores) == 6


def test_encabezado_invalido(tmp_path):
    procesos, errores = leer_archivo(escribir(tmp_path, "a,b,c,d\n1,2,3,4\n"))
    assert procesos == [] and "Encabezado" in errores[0]


def test_archivo_vacio(tmp_path):
    assert leer_archivo(escribir(tmp_path, "\n\n")) == ([], ["El archivo está vacío."])


def test_validar_proceso_limites():
    assert validar_proceso("P1", "450", "0", "1")[0] is not None
    assert validar_proceso("P1", "451", "0", "1")[0] is None
    assert validar_proceso("", "10", "0", "1")[0] is None


def test_normalizar_id():
    assert normalizar_id(" p3 ") == "P3"
    assert normalizar_id("07") == "P7"
