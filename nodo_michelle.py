
import socket
import threading
import json
import os
from datetime import datetime

PORT = 65123
HEADER = 10

NODOS = {
    "Michelle": "192.168.181.128",
    "Roberto": "192.168.181.131",
    "Jimena": "192.168.181.130",
    "Arturo": "192.168.181.132"
}

MI_NOMBRE = "Michelle"
HOST = NODOS[MI_NOMBRE]

inventario_file = "inventario_maestro.json"
clientes_file = "clientes.json"
fallas_file = "fallas.log"

articulos_en_proceso = set()

def guardar_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def cargar_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def registrar_falla(nodo):
    with open(fallas_file, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] Falla detectada en nodo: {nodo}\n")
    print(f"[FALLA] Nodo inactivo: {nodo}")

def distribuir_articulo(articulo):
    min_inventario = None
    nodo_destino = None

    for nombre, ip in NODOS.items():
        if nombre != MI_NOMBRE:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    s.connect((ip, PORT))
                    mensaje = json.dumps({
                        "tipo": "actualizar_inventario",
                        "articulo": articulo
                    }).encode()
                    s.sendall(f"{len(mensaje):<{HEADER}}".encode() + mensaje)
                    print(f"[ENVÍO] Artículo enviado a {nombre}")
                    return
            except:
                registrar_falla(nombre)

def sincronizar_cliente(cliente):
    for nombre, ip in NODOS.items():
        if nombre != MI_NOMBRE:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    mensaje = json.dumps({
                        "tipo": "nuevo_cliente",
                        "cliente": cliente
                    }).encode()
                    s.connect((ip, PORT))
                    s.sendall(f"{len(mensaje):<{HEADER}}".encode() + mensaje)
            except:
                registrar_falla(nombre)

def servidor():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print(f"Soy el nodo maestro {MI_NOMBRE} ({HOST}). Esperando conexiones...")

    while True:
        conn, addr = s.accept()
        try:
            data_len = conn.recv(HEADER)
            data = conn.recv(int(data_len))
            mensaje = data.decode()

            json_data = json.loads(mensaje)
            tipo = json_data.get("tipo")

            if tipo == "nuevo_articulo":
                articulo = json_data["articulo"]
                distribuir_articulo(articulo)

            elif tipo == "nuevo_cliente":
                clientes = cargar_json(clientes_file)
                nuevo = json_data["cliente"]
                if not any(c["id"] == nuevo["id"] for c in clientes):
                    clientes.append(nuevo)
                    guardar_json(clientes_file, clientes)
                    sincronizar_cliente(nuevo)
                    print(f"[SYNC] Cliente sincronizado: {nuevo['id']}")

            elif tipo == "verificar_bloqueo":
                art_id = json_data["articulo_id"]
                if art_id in articulos_en_proceso:
                    conn.sendall("DENEGADO".encode())
                else:
                    articulos_en_proceso.add(art_id)
                    conn.sendall("OK".encode())

        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            conn.close()

# Ejecutar
if __name__ == "__main__":
    threading.Thread(target=servidor, daemon=True).start()
    input("Presiona Enter para detener el nodo maestro...")
