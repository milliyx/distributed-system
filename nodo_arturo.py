
import socket
import threading
import json
import os
from datetime import datetime

PORT = 65123
HEADER = 10

NODOS = {
    "Michelle": "192.168.181.128",
    "Arturo": "192.168.181.131",
    "Jimena": "192.168.181.130",
    "Arturo": "192.168.181.132"
}

MI_NOMBRE = "Arturo"
HOST = NODOS[MI_NOMBRE]
MAESTRO = "Michelle"
MAESTRO_IP = NODOS[MAESTRO]

inventario_file = "inventario.json"
clientes_file = "clientes.json"
guias_file = "guias.json"

def guardar_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def cargar_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_mensaje(origen, mensaje, tipo="recibido"):
    with open("mensajes.txt", "a", encoding="utf-8") as f:
        f.write(f"[{origen}] [{tipo}]: {mensaje}\n")

def generar_serie():
    return datetime.now().strftime("%Y%m%d%H%M%S")

def guardar_guia(id_articulo, sucursal, id_cliente):
    guias = cargar_json(guias_file)
    serie = generar_serie()
    guia = {
        "id_guia": f"{id_articulo}-{serie}-{sucursal}-{id_cliente}",
        "articulo": id_articulo,
        "cliente": id_cliente,
        "sucursal": sucursal,
        "serie": serie
    }
    guias.append(guia)
    guardar_json(guias_file, guias)
    print(f"\n[INFO] Guía generada: {guia['id_guia']}")

def ver_clientes():
    clientes = cargar_json(clientes_file)
    print("\n--- CLIENTES REGISTRADOS ---")
    if not clientes:
        print("No hay clientes.")
    for cli in clientes:
        print(f"- ID: {cli['id']}, Nombre: {cli['nombre']}")
    input("Presiona Enter para continuar...")

def agregar_cliente():
    clientes = cargar_json(clientes_file)
    nuevo_id = input("ID del nuevo cliente: ").strip()
    nombre = input("Nombre del cliente: ").strip()
    if any(cli["id"] == nuevo_id for cli in clientes):
        print("[ERROR] El ID ya existe.")
        return
    cliente = {"id": nuevo_id, "nombre": nombre}
    clientes.append(cliente)
    guardar_json(clientes_file, clientes)
    sincronizar_cliente(cliente)
    print("[OK] Cliente registrado y sincronizado.")

def sincronizar_cliente(cliente):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            mensaje = json.dumps({
                "tipo": "nuevo_cliente",
                "cliente": cliente
            }).encode()
            s.connect((NODOS[MAESTRO], PORT))
            s.sendall(f"{len(mensaje):<{HEADER}}".encode() + mensaje)
    except:
        print("[WARN] No se pudo sincronizar con el maestro.")

def obtener_cliente():
    clientes = cargar_json(clientes_file)
    if not clientes:
        print("[INFO] No hay clientes. Registra uno nuevo.")
        agregar_cliente()
        clientes = cargar_json(clientes_file)

    print("\n--- Selecciona un cliente ---")
    for i, cli in enumerate(clientes):
        print(f"{i+1}. {cli['nombre']} ({cli['id']})")
    print(f"{len(clientes)+1}. Registrar nuevo cliente")

    opcion = int(input("Opción: "))
    if opcion == len(clientes) + 1:
        agregar_cliente()
        return obtener_cliente()
    return clientes[opcion - 1]["id"]

def comprar_articulo():
    inventario = cargar_json(inventario_file)
    print("\n--- INVENTARIO DISPONIBLE ---")
    for art in inventario:
        print(f"- {art['id']} ({art['nombre']}) : {art['cantidad']} unidades")

    id_art = input("ID del artículo a comprar: ").strip()
    cliente = obtener_cliente()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            mensaje_lock = json.dumps({
                "tipo": "verificar_bloqueo",
                "articulo_id": id_art
            }).encode()
            s.connect((NODOS[MAESTRO], PORT))
            s.sendall(f"{len(mensaje_lock):<{HEADER}}".encode() + mensaje_lock)
            respuesta = s.recv(16).decode()
        if respuesta != "OK":
            print("[DENEGADO] El artículo está en proceso en otro nodo.")
            return
    except:
        print("[ERROR] No se pudo contactar al maestro.")
        return

    for art in inventario:
        if art["id"] == id_art and art["cantidad"] > 0:
            art["cantidad"] -= 1
            guardar_json(inventario_file, inventario)
            guardar_guia(id_art, HOST, cliente)
            print("[ÉXITO] Compra realizada.")
            break
    else:
        print("[ERROR] Artículo no encontrado o sin stock.")
    input("Presiona Enter para continuar...")

def servidor():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print(f"Soy el nodo {MI_NOMBRE} ({HOST}). Esperando conexiones...")

    while True:
        conn, addr = s.accept()
        try:
            data_len = conn.recv(HEADER)
            data = conn.recv(int(data_len))
            mensaje = data.decode()
            json_data = json.loads(mensaje)

            if json_data.get("tipo") == "actualizar_inventario":
                inventario = cargar_json(inventario_file)
                inventario.append(json_data["articulo"])
                guardar_json(inventario_file, inventario)
                print("[ACTUALIZADO] Artículo recibido.")

            elif json_data.get("tipo") == "nuevo_cliente":
                clientes = cargar_json(clientes_file)
                nuevo = json_data["cliente"]
                if not any(c["id"] == nuevo["id"] for c in clientes):
                    clientes.append(nuevo)
                    guardar_json(clientes_file, clientes)
                    print(f"[SYNC] Cliente sincronizado: {nuevo['id']}")
        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            conn.close()

def mostrar_menu():
    print("\n------ MENÚ ROBERTO ------")
    print("1. Comprar artículo")
    print("2. Ver clientes")
    print("3. Registrar cliente")
    print("4. Ver guías de envío")
    print("5. Ver inventario")
    print("6. Salir")
    print("----------------------------")

def cliente():
    while True:
        mostrar_menu()
        opcion = input("Selecciona una opción: ")

        if opcion == "1":
            comprar_articulo()
        elif opcion == "2":
            ver_clientes()
        elif opcion == "3":
            agregar_cliente()
        elif opcion == "4":
            ver_guias()
        elif opcion == "5":
            ver_inventario()
        elif opcion == "6":
            break
        else:
            print("[ERROR] Opción inválida.")

threading.Thread(target=servidor, daemon=True).start()
cliente()


def ver_guias():
    guias = cargar_json(guias_file)
    print("\n--- GUÍAS DE ENVÍO ---")
    if not guias:
        print("No hay guías registradas.")
    for g in guias:
        print(f"{g['id_guia']} - Cliente: {g['cliente']} - Artículo: {g['articulo']}")
    input("Presiona Enter para continuar...")


def ver_inventario():
    inventario = cargar_json(inventario_file)
    print("\n--- INVENTARIO LOCAL ---")
    if not inventario:
        print("No hay artículos en el inventario.")
    for item in inventario:
        print(f"{item['id']} - {item['nombre']} : {item['cantidad']} unidades")
    input("Presiona Enter para continuar...")
