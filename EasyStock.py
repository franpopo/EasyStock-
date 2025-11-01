import tkinter as tk
from tkinter import messagebox
import sqlite3 as sq
from datetime import datetime

nombreSucursal = ""
sucursales = [""]

ventana = tk.Tk()
ventana.configure(bg="grey")
tk.Wm.wm_title(ventana, "Easy Stock")
ventana.geometry("500x500")

productos = []  # here we save products as dictionaries/acá guardamos los productos como diccionarios
ventas = []



ConexionSql = sq.connect("StockManager.db")
cursor = ConexionSql.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sucursales (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    nombre TEXT
)
""")
ConexionSql.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    stock INTEGER,
    precio REAL,
    codigo_barras TEXT UNIQUE   
)
""")
ConexionSql.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto TEXT,
    cantidad INTEGER,
    total REAL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
ConexionSql.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS venta_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER,
    producto TEXT,
    cantidad INTEGER,
    precio REAL,
    subtotal REAL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE
)
""")
ConexionSql.commit()

def AgregarTienda(nombre):
    ventanaAgregar = tk.Toplevel()
    ventanaAgregar.title("Agregar sucursal nueva")
    ventanaAgregar.geometry("500x500")
    ventanaAgregar.transient(ventana)
    ventanaAgregar.grab_set()

    PonerNombreSucursal = tk.Entry(ventanaAgregar)
    PonerNombreSucursal.grid(row=1, column=0)
    NombreSucursal = PonerNombreSucursal.get()

    cursor.execute(
        "INSERT INTO sucursales (id, nombre) VALUES (?,?)", NombreSucursal, 1)

    sucursales.append(nombre)

    ventanaAgregar.destroy()

seleccionTienda = tk.Toplevel()
seleccionTienda.title("Elegir sucursal")
seleccionTienda.geometry("500x500")
seleccionTienda.transient(ventana)
seleccionTienda.grab_set()
seleccionTienda.protocol("WM_DELETE_WINDOW", lambda: ventana.destroy())
BotonAgregarTienda = tk.Button(seleccionTienda, text="Agregar sucursal", bg="lightgreen",
                                   command=lambda: AgregarTienda())
BotonAgregarTienda.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

#BotonSeleccionarTienda = tk.Button(seleccionTienda, text=f"{}")

for nombre in sucursales:
    BotonAgregarTienda = tk.Button(seleccionTienda, text=nombre, command=lambda nombre=nombre: AbrirTienda())

# -------------------------------
#  auxiliary functions/funciones auxiliares
# -------------------------------
def EliminarProducto():
    ItemSeleccionado = ListaProductos.curselection()
    if not ItemSeleccionado:
        return
    indice = ItemSeleccionado[0]
    id_producto = productos[indice]["id"]
    ListaProductos.delete(indice)
    productos.pop(indice)
    cursor.execute("DELETE FROM productos WHERE id=?", (id_producto,))
    ConexionSql.commit()

def CerrarVentana(ventana_aux):
    ventana_aux.destroy()

def CambiarProducto():
    ItemSeleccionado = ListaProductos.curselection()
    if not ItemSeleccionado:
        return
    indice = ItemSeleccionado[0]
    producto = productos[indice]
    MenuAgregarProducto(True, producto, indice)

def CargarProductos():
    ListaProductos.delete(0, tk.END)
    productos.clear()
    # <-- cambio mínimo: traer codigo_barras también
    cursor.execute("SELECT id, nombre, stock, precio, codigo_barras FROM productos")
    filas = cursor.fetchall()
    for fila in filas:
        id_db, nombre, stock, precio, codigo_barras = fila
        productos.append({"id": id_db, "nombre": nombre, "stock": stock, "precio": precio, "codigo_barras": codigo_barras})
        detalles = f"{nombre} | stock: {stock} | precio: {precio}"
        ListaProductos.insert(tk.END, detalles)

# -------------------------------
# window register sale/ventana registrar venta
# -------------------------------
def MenuRegistrarVenta():
    MenuVenta = tk.Toplevel(ventana)
    MenuVenta.geometry("800x400")
    MenuVenta.configure(bg="lightgrey")
    MenuVenta.title("Registrar Venta")

    entradas_cant = {}


    tk.Label(MenuVenta, text="Escanear código de barras").pack(pady=5)
    EntradaCB = tk.Entry(MenuVenta)
    EntradaCB.pack(pady=5)
    EntradaCB.focus()

    frameListas = tk.Frame(MenuVenta, bg="lightgrey")
    frameListas.pack(side="top", expand=True, fill="both", padx=10, pady=10)

    # column avalibe products / Columna productos disponibles
    frameDisponibles = tk.Frame(frameListas, bg="lightgrey")
    frameDisponibles.pack(side="left", expand=True, fill="both", padx=5)
    tk.Label(frameDisponibles, text="Productos Disponibles").pack(anchor="n", pady=5)
    ListaDisponibles = tk.Listbox(frameDisponibles)
    ListaDisponibles.pack(expand=True, fill="both", pady=5, padx=5)

    for p in productos:
        detalles = f"{p['nombre']} | stock: {p['stock']} | precio: {p['precio']}"
        ListaDisponibles.insert(tk.END, detalles)

    # cart column /Columna carrito
    frameCarrito = tk.Frame(frameListas, bg="lightgrey")
    frameCarrito.pack(side="left", expand=True, fill="both", padx=5)
    tk.Label(frameCarrito, text="Carrito").pack(anchor="n", pady=5)

    frameItemsCarrito = tk.Frame(frameCarrito, bg="lightgrey")
    frameItemsCarrito.pack(expand=True, fill="both", pady=5, padx=5)

    # function to add products to cart by barcode / Función agregar producto al carrito por código de barras
    def agregar_por_cb(event):
        codigo = EntradaCB.get().strip()
        EntradaCB.delete(0, tk.END)
        if codigo == "":
            return
        producto = next((p for p in productos if p.get("codigo_barras") == codigo), None)



        if not producto:
            messagebox.showerror("Error", f"Producto con código {codigo} no registrado")
            return

        for widget in frameItemsCarrito.winfo_children():
            if getattr(widget, "producto_id", None) == producto['id']:
                entry = entradas_cant[producto['id']]
                entry.delete(0, tk.END)
                entry.insert(0, str(int(entry.get() or 0) + 1))
                return

        fila = tk.Frame(frameItemsCarrito, bg="lightgrey")
        fila.pack(fill="x", pady=2)
        fila.producto_id = producto['id']
        tk.Label(fila, text=producto['nombre'], width=25, anchor="w").pack(side="left")
        e = tk.Entry(fila, width=5)
        e.pack(side="left", padx=5)
        e.insert(0, "1")
        entradas_cant[producto['id']] = e


    EntradaCB.bind("<Return>", agregar_por_cb)

    # function add to cart / Función agregar al carrito
    def agregar_al_carrito(event):
        seleccion = ListaDisponibles.curselection()
        if not seleccion:
            return
        idx = seleccion[0]
        p = productos[idx]
        for widget in frameItemsCarrito.winfo_children():
            if isinstance(widget, tk.Frame) and getattr(widget, "producto_id", None) == p['id']:
                return  # ya agregado
        fila = tk.Frame(frameItemsCarrito, bg="lightgrey")
        fila.pack(fill="x", pady=2)
        fila.producto_id = p['id']
        tk.Label(fila, text=p['nombre'], width=25, anchor="w").pack(side="left")
        e = tk.Entry(fila, width=5)
        e.pack(side="left", padx=5)
        e.insert(0, "1")  # unificación: cantidad inicial
        entradas_cant[p['id']] = e

    ListaDisponibles.bind("<Double-Button-1>", agregar_al_carrito)

    # button frame / Frame botones
    frameBotones = tk.Frame(MenuVenta, bg="lightgrey")
    frameBotones.pack(side="bottom", expand=False, fill="x", padx=10, pady=10)

    def procesar_venta():
        lineas = []
        total_venta = 0.0

        # check first if there is enough stock / Validar primero si hay stock suficiente
        for id_prod, entry in entradas_cant.items():
            cant = int(entry.get()) if entry.get() else 0
            if cant <= 0:
                continue
            p = next(x for x in productos if x['id'] == id_prod)
            stock_disp = int(p['stock'])
            if cant > stock_disp:
                messagebox.showerror("Error", f"No hay suficiente stock de {p['nombre']}.\n"
                                              f"Stock disponible: {stock_disp}, pedido: {cant}")
                return  # cancel the entire sale / cancela toda la venta

        # if it pass the validation, set up the sale / Si pasa la validación, armar la venta
        for id_prod, entry in entradas_cant.items():
            cant = int(entry.get()) if entry.get() else 0
            if cant <= 0:
                continue
            p = next(x for x in productos if x['id'] == id_prod)
            precio = float(p['precio'])
            subtotal = cant * precio
            lineas.append((p, cant, precio, subtotal))
            total_venta += subtotal

        if total_venta <= 0:
            messagebox.showinfo("Venta", "No hay cantidades válidas.")
            return

        # Insertar en tabla ventas
        cursor.execute(
            "INSERT INTO ventas (producto, cantidad, total) VALUES (?, ?, ?)",
            (None, None, total_venta)
        )
        venta_id = cursor.lastrowid

        # insert the items and  / Insertar los ítems y actualizar stock
        for p, cant, precio, subtotal in lineas:
            cursor.execute(
                "INSERT INTO venta_items (venta_id, producto, cantidad, precio, subtotal) VALUES (?, ?, ?, ?, ?)",
                (venta_id, p['nombre'], cant, precio, subtotal)
            )
            nuevo_stock = int(p['stock']) - cant
            p['stock'] = nuevo_stock
            cursor.execute("UPDATE productos SET stock=? WHERE id=?", (nuevo_stock, p['id']))

        ConexionSql.commit()
        CargarProductos()
        MenuVenta.destroy()

    botonConfirmar = tk.Button(frameBotones, text="Confirmar Venta", command=procesar_venta, bg="lightgreen")
    botonConfirmar.pack(expand=True, fill="both", pady=5)
    botonCancelar = tk.Button(frameBotones, text="Cancelar", command=lambda: CerrarVentana(MenuVenta), bg="tomato")
    botonCancelar.pack(expand=True, fill="both", pady=5)

# -------------------------------
# HISTORIAL DE VENTAS
# -------------------------------

def MenuHistorialVentas():
    MenuHist = tk.Toplevel(ventana)
    MenuHist.geometry("800x400")
    MenuHist.configure(bg="lightgrey")
    MenuHist.title("Historial de Ventas")

    frameListas = tk.Frame(MenuHist, bg="lightgrey")
    frameListas.pack(expand=True, fill="both", padx=10, pady=10)

    frameVentas = tk.Frame(frameListas, bg="lightgrey")
    frameVentas.pack(side="left", expand=True, fill="both", padx=5)
    tk.Label(frameVentas, text="Ventas").pack(anchor="n", pady=5)
    ListaVentas = tk.Listbox(frameVentas)
    ListaVentas.pack(expand=True, fill="both", pady=5, padx=5)

    frameDetalle = tk.Frame(frameListas, bg="lightgrey")
    frameDetalle.pack(side="left", expand=True, fill="both", padx=5)
    tk.Label(frameDetalle, text="Detalle de la venta").pack(anchor="n", pady=5)
    TextoDetalle = tk.Text(frameDetalle, height=10)
    TextoDetalle.pack(expand=True, fill="both", padx=5, pady=5)

    ventas.clear()
    cursor.execute("SELECT id, total, fecha FROM ventas ORDER BY fecha DESC")
    filas = cursor.fetchall()
    for id_db, total, fecha in filas:
        ventas.append({"id": id_db, "total": total, "fecha": fecha})
        ListaVentas.insert(tk.END, f"{fecha} | Total: ${total}")

    def mostrar_detalle(event):
        sel = ListaVentas.curselection()
        if not sel:
            return
        venta = ventas[sel[0]]
        venta_id = venta["id"]

        TextoDetalle.delete("1.0", tk.END)
        cursor.execute("SELECT producto, cantidad, precio, subtotal FROM venta_items WHERE venta_id=?", (venta_id,))
        items = cursor.fetchall()

        if items:
            total_calc = 0.0
            for prod, cant, precio, subtotal in items:
                TextoDetalle.insert(tk.END, f"{prod} | Cantidad: {cant} | Precio: {precio} | Subtotal: {subtotal}\n")
                total_calc += float(subtotal)
            TextoDetalle.insert(tk.END, f"\nTotal venta: {total_calc}")
        else:
            cursor.execute("SELECT producto, cantidad, total FROM ventas WHERE id=?", (venta_id,))
            r = cursor.fetchone()
            if r and r[0] is not None:
                prod, cant, total = r
                TextoDetalle.insert(tk.END, f"{prod} | Cantidad: {cant} | Total: {total}\n")
                TextoDetalle.insert(tk.END, f"\nTotal venta: {total}")
            else:
                TextoDetalle.insert(tk.END, "Sin ítems registrados para esta venta.")

    ListaVentas.bind("<<ListboxSelect>>", mostrar_detalle)

    def EliminarVenta():
        seleccion = ListaVentas.curselection()
        if not seleccion:
            return
        indice = seleccion[0]
        venta = ventas[indice]
        confirmar = messagebox.askyesno("Confirmar", f"¿Seguro que desea eliminar la venta del {venta['fecha']}?")
        if not confirmar:
            return

        venta_id = venta["id"]
        cursor.execute("DELETE FROM venta_items WHERE venta_id=?", (venta_id,))
        cursor.execute("DELETE FROM ventas WHERE id=?", (venta_id,))
        ConexionSql.commit()

        ventas.pop(indice)
        ListaVentas.delete(indice)
        TextoDetalle.delete("1.0", tk.END)
        TextoDetalle.insert(tk.END, "Venta eliminada.")

    BotonEliminar = tk.Button(MenuHist, text="Eliminar venta", bg="red", fg="white", command=EliminarVenta)
    BotonEliminar.pack(pady=5, expand = True, fill = "both", padx = 200)

    BotonTop = tk.Button(MenuHist, text="Mejores Productos", bg="lightblue", command=MenuTopMensual)
    BotonTop.pack(pady=5, expand = True, fill = "both", padx = 200)

    botonCerrar = tk.Button(MenuHist, text="Cerrar", command=lambda: CerrarVentana(MenuHist), bg="tomato")
    botonCerrar.pack(side="bottom", expand = True, fill = "both", padx=200, pady=5)

# -------------------------------
# TOP MENSUAL
# -------------------------------
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

def MenuTopMensual():
    top_window = tk.Toplevel(ventana)
    top_window.title("Top Productos del Mes")
    top_window.geometry("600x400")
    top_window.configure(bg="lightgrey")

    mes_actual = datetime.now().replace(day=1)

    frame_header = tk.Frame(top_window, bg="lightgrey")
    frame_header.pack(fill="x", pady=5)

    btn_izq = tk.Button(frame_header, text="<--", width=5)
    btn_izq.pack(side="left", padx=10)
    lbl_fecha = tk.Label(frame_header, text="", font=("Arial", 14), bg="lightgrey")
    lbl_fecha.pack(side="left", expand=True)
    btn_der = tk.Button(frame_header, text="-->", width=5)
    btn_der.pack(side="right", padx=10)

    # Frame con grid para alinear títulos y listbox
    frame_listbox = tk.Frame(top_window, bg="lightgrey")
    frame_listbox.pack(expand=True, fill="both", padx=10, pady=10)

    frame_listbox.columnconfigure(0, weight=1)
    frame_listbox.columnconfigure(1, weight=1)
    frame_listbox.rowconfigure(1, weight=1)

    # Encabezados
    tk.Label(frame_listbox, text="Más unidades vendidas", bg="lightgrey", font=("Arial", 12, "bold"))\
        .grid(row=0, column=0, sticky="n")
    tk.Label(frame_listbox, text="Más ingresos generados", bg="lightgrey", font=("Arial", 12, "bold"))\
        .grid(row=0, column=1, sticky="n")

    # Listbox alineados
    listbox_unidades = tk.Listbox(frame_listbox)
    listbox_unidades.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    listbox_ingresos = tk.Listbox(frame_listbox)
    listbox_ingresos.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

    def actualizar_listbox():
        lbl_fecha.config(text=f"{MESES_ES[mes_actual.month-1]} {mes_actual.year}")
        mes_str = mes_actual.strftime("%Y-%m")

        cursor.execute("""
            SELECT vi.producto, SUM(vi.cantidad) AS total_vendido, SUM(vi.subtotal) AS ingresos
            FROM venta_items vi
            JOIN ventas v ON vi.venta_id = v.id
            WHERE strftime('%Y-%m', v.fecha) = ?
            GROUP BY vi.producto
            ORDER BY total_vendido DESC
        """, (mes_str,))
        resultados_unidades = cursor.fetchall()

        cursor.execute("""
            SELECT vi.producto, SUM(vi.cantidad) AS total_vendido, SUM(vi.subtotal) AS ingresos
            FROM venta_items vi
            JOIN ventas v ON vi.venta_id = v.id
            WHERE strftime('%Y-%m', v.fecha) = ?
            GROUP BY vi.producto
            ORDER BY ingresos DESC
        """, (mes_str,))
        resultados_ingresos = cursor.fetchall()

        listbox_unidades.delete(0, tk.END)
        for fila in resultados_unidades:
            listbox_unidades.insert(tk.END, f"{fila[0]} | {fila[1]} unidades")

        listbox_ingresos.delete(0, tk.END)
        for fila in resultados_ingresos:
            listbox_ingresos.insert(tk.END, f"{fila[0]} | ${fila[2]:.2f}")

    def cambiar_mes(meses):
        nonlocal mes_actual
        año = mes_actual.year + ((mes_actual.month + meses - 1) // 12)
        mes = (mes_actual.month + meses - 1) % 12 + 1
        mes_actual = mes_actual.replace(year=año, month=mes)
        actualizar_listbox()

    btn_izq.config(command=lambda: cambiar_mes(-1))
    btn_der.config(command=lambda: cambiar_mes(1))

    actualizar_listbox()


    btn_izq.config(command=lambda: cambiar_mes(-1))
    btn_der.config(command=lambda: cambiar_mes(1))

    actualizar_listbox()

# -------------------------------
# AGREGAR PRODUCTOS CON VALIDACION
# -------------------------------
def MenuAgregarProducto(ModificandoProducto, producto=None, indice=None):
    MenuAgregar = tk.Toplevel(ventana)
    MenuAgregar.geometry("500x300")
    MenuAgregar.configure(bg="grey")

    for i in range(4):
        MenuAgregar.rowconfigure(i, weight=1)
    for i in range(3):
        MenuAgregar.columnconfigure(i, weight=1)

    if ModificandoProducto:
        tk.Wm.wm_title(MenuAgregar, "Modificar Producto")
    else:
        tk.Wm.wm_title(MenuAgregar, "Agregar Producto")

    # <-- cambio mínimo: agrego campo texto para codigo de barras
    tk.Label(MenuAgregar, text="Código de barras").grid(row=2, column=0, pady=10)
    TextoCB = tk.Entry(MenuAgregar)
    TextoCB.grid(row=3, column=0, sticky="nsew", pady=5)

    if ModificandoProducto and "codigo_barras" in producto:
        TextoCB.insert(0, producto.get("codigo_barras", ""))

    tk.Label(MenuAgregar, text="Nombre").grid(row=0, column=0, pady=30)
    TextoNombre = tk.Entry(MenuAgregar)
    TextoNombre.grid(row=1, column=0, sticky="nsew", pady=30)
    if ModificandoProducto:
        TextoNombre.insert(0, producto["nombre"])

    tk.Label(MenuAgregar, text="Stock").grid(row=0, column=1)
    TextoStock = tk.Entry(MenuAgregar)
    TextoStock.grid(row=1, column=1, sticky="nsew", pady=30)
    if ModificandoProducto:
        TextoStock.insert(0, producto["stock"])

    tk.Label(MenuAgregar, text="Precio").grid(row=0, column=2)
    TextoPrecio = tk.Entry(MenuAgregar)
    TextoPrecio.grid(row=1, column=2, sticky="nsew", pady=30)
    if ModificandoProducto:
        TextoPrecio.insert(0, producto["precio"])

    # Validación
    def validar_entero(text):
        return text.isdigit() or text == ""
    def validar_decimal(text):
        import re
        return re.fullmatch(r"\d*\.?\d{0,2}", text) is not None or text == ""

    vcmd_int = (MenuAgregar.register(validar_entero), '%P')
    vcmd_dec = (MenuAgregar.register(validar_decimal), '%P')
    TextoStock.config(validate="key", validatecommand=vcmd_int)
    TextoPrecio.config(validate="key", validatecommand=vcmd_dec)

    def aceptar():
        nuevo = {
            "nombre": TextoNombre.get(),
            "stock": TextoStock.get(),
            "precio": TextoPrecio.get(),
            "codigo_barras": TextoCB.get()
        }
        if ModificandoProducto:
            productos[indice] = nuevo
            ListaProductos.delete(indice)
            ListaProductos.insert(indice, f"{nuevo['nombre']} | stock: {nuevo['stock']} | precio: {nuevo['precio']}")
            # <-- UPDATE incluyendo codigo_barras
            cursor.execute("UPDATE productos SET nombre=?, stock=?, precio=?, codigo_barras=? WHERE id=?",
                           (nuevo["nombre"], nuevo["stock"], nuevo["precio"], nuevo["codigo_barras"], producto["id"]))
            ConexionSql.commit()
        else:
            productos.append(nuevo)
            ListaProductos.insert(tk.END, f"{nuevo['nombre']} | stock: {nuevo['stock']} | precio: {nuevo['precio']}")
            # <-- INSERT incluyendo codigo_barras
            cursor.execute("INSERT INTO productos (nombre, stock, precio, codigo_barras) VALUES (?, ?, ?, ?)",
                           (nuevo["nombre"], nuevo["stock"], nuevo["precio"], nuevo["codigo_barras"]))
            ConexionSql.commit()
        MenuAgregar.destroy()

    BotonAceptar = tk.Button(MenuAgregar, text="Aceptar", command=aceptar)
    BotonAceptar.grid(row=2, column=1, sticky="nsew")
    BotonCancelar = tk.Button(MenuAgregar, text="Cancelar", command=lambda: CerrarVentana(MenuAgregar))
    BotonCancelar.grid(row=3, column=1, sticky="nsew")

# -------------------------------
# INTERFAZ PRINCIPAL
# -------------------------------
ventana.rowconfigure([0,1,2,3,4,5], weight=1)
ventana.columnconfigure(0, weight=1)
ventana.columnconfigure(1, weight=1)

ListaProductos = tk.Listbox(ventana, width=40, height=10, font=("Arial", 15), bg="grey")
ListaProductos.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

CargarProductos()

BotonAgregar = tk.Button(ventana, text="Agregar producto", bg="lightgreen",
                         command=lambda: MenuAgregarProducto(False))
BotonAgregar.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

BotonModificar = tk.Button(ventana, text="Modificar producto", bg="sky blue", command=CambiarProducto)
BotonModificar.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

BotonBorrar = tk.Button(ventana, text="Eliminar producto", bg="tomato", command=EliminarProducto)
BotonBorrar.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

BotonVenta = tk.Button(ventana, text="Registrar Venta", bg="orange", command=MenuRegistrarVenta)
BotonVenta.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

BotonHistorialVentas = tk.Button(ventana, text="Historial de ventas", bg="violet", command=MenuHistorialVentas)
BotonHistorialVentas.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

# -------------------------------
# CIERRE
# -------------------------------
def on_closing():
    ConexionSql.commit()
    ConexionSql.close()
    ventana.destroy()

ventana.protocol("WM_DELETE_WINDOW", on_closing)
ventana.mainloop()
