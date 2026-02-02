"""
Refactorización del proyecto "Easy Stock" usando CustomTkinter para una interfaz más estética
y modularizable. Mantiene la lógica esencial: gestión de tiendas, productos, ventas e historial.

Dependencias:
  pip install customtkinter pandas openpyxl

Notas:
- Este archivo está pensado como base. Para producción: separar en módulos (db.py, ui/*.py, utils.py).
- Paleta: neutros + acento verde. Diseño responsivo usando grid/pack combinado y frames expandibles.

"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog
import sqlite3
from datetime import datetime
import pandas as pd

def bring_to_front(win):
    win.lift()
    win.attributes("-topmost", True)
    win.after(50, lambda: win.attributes("-topmost", False))
    win.focus_force()


# -------------------------
# Config UI global
# -------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")  # puedes cambiar por "dark-blue" etc.

DB_FILE = "StockManager.db"
PASSWORD = "2000"
INACTIVITY_MS = 5 * 60 * 1000  # 5 minutos

# -------------------------
# DB Manager (encapsula acceso a sqlite)
# -------------------------
class DBManager:
    def __init__(self, filename=DB_FILE):
        self.conn = sqlite3.connect(filename, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._ensure_schema()

    def _ensure_schema(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS tiendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            stock INTEGER,
            precio REAL,
            id_tienda INTEGER,
            codigo_barras TEXT UNIQUE
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            cantidad INTEGER,
            total REAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.cursor.execute("""
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
        self.conn.commit()

    # Tiendas
    def list_tiendas(self):
        self.cursor.execute("SELECT id, nombre FROM tiendas ORDER BY id")
        return [dict(r) for r in self.cursor.fetchall()]

    def add_tienda(self, nombre):
        self.cursor.execute("INSERT INTO tiendas (nombre) VALUES (?)", (nombre,))
        self.conn.commit()
        return self.cursor.lastrowid

    # Productos
    def list_productos(self, id_tienda=None):
        if id_tienda is None:
            self.cursor.execute("SELECT id, nombre, stock, precio, id_tienda, codigo_barras FROM productos")
        else:
            self.cursor.execute(
                "SELECT id, nombre, stock, precio, id_tienda, codigo_barras FROM productos WHERE id_tienda = ?",
                (id_tienda,)
            )
        return [dict(r) for r in self.cursor.fetchall()]

    def add_producto(self, nombre, stock, precio, id_tienda, codigo_barras=None):
        try:
            self.cursor.execute(
                "INSERT INTO productos (nombre, stock, precio, id_tienda, codigo_barras) VALUES (?, ?, ?, ?, ?)",
                (nombre, int(stock), float(precio), id_tienda, codigo_barras)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            raise

    def update_producto(self, prod_id, nombre, stock, precio, codigo_barras):
        self.cursor.execute(
            "UPDATE productos SET nombre=?, stock=?, precio=?, codigo_barras=? WHERE id=?",
            (nombre, int(stock), float(precio), codigo_barras, prod_id)
        )
        self.conn.commit()

    def delete_producto(self, prod_id):
        self.cursor.execute("DELETE FROM productos WHERE id=?", (prod_id,))
        self.conn.commit()

    # Ventas
    def create_venta(self, lineas, total):
        # lineas: list of dicts {producto, cantidad, precio, subtotal}
        self.cursor.execute("INSERT INTO ventas (producto, cantidad, total) VALUES (?, ?, ?)", (None, None, total))
        venta_id = self.cursor.lastrowid
        for l in lineas:
            self.cursor.execute(
                "INSERT INTO venta_items (venta_id, producto, cantidad, precio, subtotal) VALUES (?, ?, ?, ?, ?)",
                (venta_id, l['producto'], l['cantidad'], l['precio'], l['subtotal'])
            )
            # actualizar stock
            self.cursor.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (l['cantidad'], l['producto_id']))
        self.conn.commit()
        return venta_id

    def list_ventas(self):
        self.cursor.execute("SELECT id, total, fecha FROM ventas ORDER BY fecha DESC")
        return [dict(r) for r in self.cursor.fetchall()]

    def list_items_by_venta(self, venta_id):
        self.cursor.execute("SELECT producto, cantidad, precio, subtotal FROM venta_items WHERE venta_id = ?", (venta_id,))
        return [dict(r) for r in self.cursor.fetchall()]

    def delete_venta(self, venta_id):
        self.cursor.execute("DELETE FROM venta_items WHERE venta_id = ?", (venta_id,))
        self.cursor.execute("DELETE FROM ventas WHERE id = ?", (venta_id,))
        self.conn.commit()

    def top_por_mes(self, year_month):
        # year_month: 'YYYY-MM'
        self.cursor.execute(
            """
            SELECT vi.producto, SUM(vi.cantidad) AS total_vendido, SUM(vi.subtotal) AS ingresos
            FROM venta_items vi
            JOIN ventas v ON vi.venta_id = v.id
            WHERE strftime('%Y-%m', v.fecha) = ?
            GROUP BY vi.producto
            ORDER BY total_vendido DESC
            """,
            (year_month,)
        )
        unidades = [dict(r) for r in self.cursor.fetchall()]

        self.cursor.execute(
            """
            SELECT vi.producto, SUM(vi.cantidad) AS total_vendido, SUM(vi.subtotal) AS ingresos
            FROM venta_items vi
            JOIN ventas v ON vi.venta_id = v.id
            WHERE strftime('%Y-%m', v.fecha) = ?
            GROUP BY vi.producto
            ORDER BY ingresos DESC
            """,
            (year_month,)
        )
        ingresos = [dict(r) for r in self.cursor.fetchall()]
        return unidades, ingresos

    def close(self):
        self.conn.commit()
        self.conn.close()


# -------------------------
# Ventanas y componentes (UI)
# -------------------------
class AddEditProductWindow(ctk.CTkToplevel):
    def __init__(self, parent, db: DBManager, tienda_id, producto=None, callback=None):
        super().__init__(parent)
        bring_to_front(self)
        self.db = db
        self.tienda_id = tienda_id
        self.producto = producto
        self.callback = callback
        self.title("Agregar producto" if producto is None else "Modificar producto")
        self.geometry("500x360")
        self.configure(padx=16, pady=16)

        # Entradas
        self.entry_codigo = ctk.CTkEntry(self, placeholder_text="Código de barras (opcional)")
        self.entry_nombre = ctk.CTkEntry(self, placeholder_text="Nombre")
        self.entry_stock = ctk.CTkEntry(self, placeholder_text="Stock (entero)")
        self.entry_precio = ctk.CTkEntry(self, placeholder_text="Precio (ej: 12.50)")

        self.entry_codigo.pack(fill='x', pady=6)
        self.entry_nombre.pack(fill='x', pady=6)
        self.entry_stock.pack(fill='x', pady=6)
        self.entry_precio.pack(fill='x', pady=6)

        frame = ctk.CTkFrame(self, height=60)
        frame.pack(fill='x', pady=10)
        frame.pack_propagate(False)



        if self.producto:
            self.entry_codigo.insert(0, self.producto.get('codigo_barras') or "")
            self.entry_nombre.insert(0, self.producto['nombre'])
            self.entry_stock.insert(0, str(self.producto['stock']))
            self.entry_precio.insert(0, str(self.producto['precio']))

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill='x', pady=8)
        btn_ok = ctk.CTkButton(btn_frame, text="Aceptar", command=self.aceptar)
        btn_cancel = ctk.CTkButton(btn_frame, text="Cancelar", command=self.destroy)
        btn_ok.pack(side='left', expand=True, padx=6)
        btn_cancel.pack(side='right', expand=True, padx=6)

    def aceptar(self):
        codigo = self.entry_codigo.get().strip() or None
        nombre = self.entry_nombre.get().strip()
        stock = self.entry_stock.get().strip() or "0"
        precio = self.entry_precio.get().strip() or "0"

        # Validaciones simples
        if not nombre:
            messagebox.showerror("Error", "El nombre no puede quedar vacío")
            return
        try:
            stock_i = int(stock)
            precio_f = float(precio)
        except ValueError:
            messagebox.showerror("Error", "Stock debe ser entero y precio numérico")
            return

        try:
            if self.producto:
                self.db.update_producto(self.producto['id'], nombre, stock_i, precio_f, codigo)
            else:
                self.db.add_producto(nombre, stock_i, precio_f, self.tienda_id, codigo)
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Ya existe un producto con ese código de barras")
            return

        if self.callback:
            self.callback()
        self.destroy()


class SaleWindow(ctk.CTkToplevel):
    def __init__(self, parent, db: DBManager, productos, refresh_callback):
        super().__init__(parent)
        bring_to_front(self)
        self.db = db
        self.productos = productos  # lista de dicts con id, nombre, stock, precio, codigo_barras
        self.refresh_callback = refresh_callback
        self.title("Registrar Venta")
        self.geometry("900x520")
        self.configure(padx=12, pady=12)

        # Escaneo / buscar
        self.label_scan = ctk.CTkLabel(self, text="Escanear/Ingresar código de barras y presionar Enter")
        self.entry_cb = ctk.CTkEntry(self)
        self.entry_cb.bind('<Return>', self.agregar_por_cb)
        self.label_scan.pack(pady=6)
        self.entry_cb.pack(fill='x', pady=6)

        # Content frames
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill='both', pady=6)
        left = ctk.CTkFrame(frame)
        right = ctk.CTkFrame(frame)
        left.pack(side='left', expand=True, fill='both', padx=6)
        right.pack(side='right', expand=True, fill='both', padx=6)

        # Left: disponibles
        ctk.CTkLabel(left, text="Productos disponibles").pack(anchor='n', pady=6)
        self.lb_disponibles = tk.Listbox(left)
        self.lb_disponibles.pack(expand=True, fill='both', padx=6, pady=6)
        for p in self.productos:
            self.lb_disponibles.insert(tk.END, f"{p['nombre']} | stock: {p['stock']} | ${p['precio']}")
        self.lb_disponibles.bind('<Double-Button-1>', self.agregar_al_carrito)

        # Right: carrito
        ctk.CTkLabel(right, text="Carrito").pack(anchor='n', pady=6)
        self.frame_items = ctk.CTkScrollableFrame(right)
        self.frame_items.pack(expand=True, fill='both', padx=6, pady=6)
        self.entradas_cant = {}
        # Botones
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill='x', pady=6)
        btn_confirm = ctk.CTkButton(btn_frame, text="Confirmar Venta", command=self.procesar_venta)
        btn_cancel = ctk.CTkButton(btn_frame, text="Cancelar", command=self.destroy)
        btn_confirm.pack(side='left', expand=True, padx=8)
        btn_cancel.pack(side='right', expand=True, padx=8)

    def agregar_por_cb(self, event=None):
        codigo = self.entry_cb.get().strip()
        self.entry_cb.delete(0, tk.END)
        if not codigo:
            return
        producto = next((p for p in self.productos if (p.get('codigo_barras') or '') == codigo), None)
        if not producto:
            messagebox.showerror("Error", f"Producto con código {codigo} no registrado")
            return
        self._agregar_item(producto)

    def agregar_al_carrito(self, event=None):
        sel = self.lb_disponibles.curselection()
        if not sel:
            return
        p = self.productos[sel[0]]
        self._agregar_item(p)

    def _agregar_item(self, producto):
        # evita duplicados: si existe incrementa
        for child in self.frame_items.winfo_children():
            if getattr(child, 'producto_id', None) == producto['id']:
                entry = self.entradas_cant[producto['id']]
                entry.delete(0, tk.END)
                entry.insert(0, str(int(entry.get() or '0') + 1))
                return
        fila = ctk.CTkFrame(self.frame_items)
        fila.producto_id = producto['id']
        fila.pack(fill='x', pady=6, padx=6)
        lbl = ctk.CTkLabel(fila, text=producto['nombre'], anchor='w')
        lbl.pack(side='left', expand=True)
        e = ctk.CTkEntry(fila, width=80)
        e.pack(side='right')
        e.insert(0, '1')
        self.entradas_cant[producto['id']] = e

    def procesar_venta(self):
        lineas = []
        total = 0.0
        # Validar stocks
        for pid, entry in self.entradas_cant.items():
            try:
                cant = int(entry.get())
            except ValueError:
                messagebox.showerror("Error", "Cantidades inválidas")
                return
            if cant <= 0:
                continue
            p = next((x for x in self.productos if x['id'] == pid), None)
            if p is None:
                continue
            if cant > p['stock']:
                messagebox.showerror("Error", f"Stock insuficiente para {p['nombre']}: disponible {p['stock']}, pedido {cant}")
                return
            subtotal = cant * float(p['precio'])
            lineas.append({
                'producto': p['nombre'],
                'producto_id': p['id'],
                'cantidad': cant,
                'precio': float(p['precio']),
                'subtotal': subtotal
            })
            total += subtotal

        if total <= 0:
            messagebox.showinfo("Venta", "No hay cantidades válidas")
            return

        self.db.create_venta(lineas, total)
        messagebox.showinfo("OK", f"Venta registrada por ${total:.2f}")
        if self.refresh_callback:
            self.refresh_callback()
        self.destroy()


class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, parent, db: DBManager):
        super().__init__(parent)
        bring_to_front(self)
        self.db = db
        self.title("Historial de Ventas")
        self.geometry("860x480")
        self.configure(padx=12, pady=12)

        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill='both')
        left = ctk.CTkFrame(frame)
        right = ctk.CTkFrame(frame)
        left.pack(side='left', expand=True, fill='both', padx=6, pady=6)
        right.pack(side='right', expand=True, fill='both', padx=6, pady=6)

        ctk.CTkLabel(left, text='Ventas').pack(anchor='n', pady=6)
        self.lb_ventas = tk.Listbox(left)
        self.lb_ventas.pack(expand=True, fill='both', padx=6, pady=6)
        self.lb_ventas.bind('<<ListboxSelect>>', self.mostrar_detalle)

        ctk.CTkLabel(right, text='Detalle').pack(anchor='n', pady=6)
        self.txt_detalle = ctk.CTkTextbox(right, width=1, height=1)
        self.txt_detalle.pack(expand=True, fill='both', padx=6, pady=6)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill='x', pady=6)
        btn_del = ctk.CTkButton(btn_frame, text='Eliminar venta', command=self.eliminar_venta)
        btn_top = ctk.CTkButton(btn_frame, text='Top mensual', command=self.abrir_top)
        btn_close = ctk.CTkButton(btn_frame, text='Cerrar', command=self.destroy)
        btn_del.pack(side='left', expand=True, padx=8)
        btn_top.pack(side='left', expand=True, padx=8)
        btn_close.pack(side='right', expand=True, padx=8)

        self.ventas = []
        self.cargar_ventas()

    def cargar_ventas(self):
        self.ventas = self.db.list_ventas()
        self.lb_ventas.delete(0, tk.END)
        for v in self.ventas:
            self.lb_ventas.insert(tk.END, f"{v['fecha']} | Total: ${v['total']}")

    def mostrar_detalle(self, event=None):
        sel = self.lb_ventas.curselection()
        if not sel:
            return
        venta = self.ventas[sel[0]]
        items = self.db.list_items_by_venta(venta['id'])
        self.txt_detalle.delete('0.0', tk.END)
        if items:
            total_calc = 0.0
            for it in items:
                self.txt_detalle.insert(tk.END, f"{it['producto']} | Cant: {it['cantidad']} | Precio: {it['precio']} | Sub: {it['subtotal']}\n")
                total_calc += float(it['subtotal'])
            self.txt_detalle.insert(tk.END, f"\nTotal venta: {total_calc}")
        else:
            self.txt_detalle.insert(tk.END, "Sin ítems registrados para esta venta.")

    def eliminar_venta(self):
        sel = self.lb_ventas.curselection()
        if not sel:
            return
        idx = sel[0]
        venta = self.ventas[idx]
        if not messagebox.askyesno("Confirmar", f"¿Eliminar venta del {venta['fecha']}?"):
            return
        self.db.delete_venta(venta['id'])
        self.cargar_ventas()
        self.txt_detalle.delete('0.0', tk.END)

    def abrir_top(self):
        TopWindow(self, self.db)


class TopWindow(ctk.CTkToplevel):
    MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

    def __init__(self, parent, db: DBManager):
        super().__init__(parent)
        bring_to_front(self)
        self.db = db
        self.mes_actual = datetime.now().replace(day=1)
        self.title("Top Productos del Mes")
        self.geometry("760x420")
        self.configure(padx=12, pady=12)

        header = ctk.CTkFrame(self)
        header.pack(fill='x', pady=6)
        btn_prev = ctk.CTkButton(header, text='<', width=40, command=lambda: self.cambiar_mes(-1))
        btn_next = ctk.CTkButton(header, text='>', width=40, command=lambda: self.cambiar_mes(1))
        self.lbl_fecha = ctk.CTkLabel(header, text='')
        btn_prev.pack(side='left', padx=6)
        self.lbl_fecha.pack(side='left', expand=True)
        btn_next.pack(side='right', padx=6)

        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill='both', pady=6)
        left = ctk.CTkFrame(frame)
        right = ctk.CTkFrame(frame)
        left.pack(side='left', expand=True, fill='both', padx=6)
        right.pack(side='right', expand=True, fill='both', padx=6)

        ctk.CTkLabel(left, text='Más unidades vendidas').pack(anchor='n', pady=6)
        self.lb_unidades = tk.Listbox(left)
        self.lb_unidades.pack(expand=True, fill='both', padx=6, pady=6)

        ctk.CTkLabel(right, text='Más ingresos generados').pack(anchor='n', pady=6)
        self.lb_ingresos = tk.Listbox(right)
        self.lb_ingresos.pack(expand=True, fill='both', padx=6, pady=6)

        self.actualizar_listbox()

    def cambiar_mes(self, meses):
        año = self.mes_actual.year + ((self.mes_actual.month + meses - 1) // 12)
        mes = (self.mes_actual.month + meses - 1) % 12 + 1
        self.mes_actual = self.mes_actual.replace(year=año, month=mes)
        self.actualizar_listbox()

    def actualizar_listbox(self):
        self.lbl_fecha.configure(text=f"{self.MESES_ES[self.mes_actual.month-1]} {self.mes_actual.year}")
        mes_str = self.mes_actual.strftime('%Y-%m')
        unidades, ingresos = self.db.top_por_mes(mes_str)
        self.lb_unidades.delete(0, tk.END)
        for u in unidades:
            self.lb_unidades.insert(tk.END, f"{u['producto']} | {int(u['total_vendido'])} unidades")
        self.lb_ingresos.delete(0, tk.END)
        for inc in ingresos:
            self.lb_ingresos.insert(tk.END, f"{inc['producto']} | ${float(inc['ingresos']):.2f}")


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Easy Stock - Refactor")
        self.geometry("1100x700")
        self.minsize(800, 600)
        self.db = DBManager()
        self.tienda_id = None
        self.productos = []
        self.contraseña_ok = False
        self._iniciar_ui()
        self.after(INACTIVITY_MS, self._pedir_contraseña_periodico)
        self._seleccionar_tienda_inicio()

    # ------------------ UI principal ------------------
    def _iniciar_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure((0,1), weight=1)

        # Header - buscador
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, columnspan=2, sticky='nsew', padx=12, pady=12)
        header.grid_columnconfigure(0, weight=1)
        self.entry_buscar = ctk.CTkEntry(header, placeholder_text='Buscar producto...')
        self.entry_buscar.grid(row=0, column=0, sticky='nsew', padx=8, pady=6)
        self.entry_buscar.bind('<KeyRelease>', self.filtrar_lista)

        # Lista principal
        frame_central = ctk.CTkFrame(self)
        frame_central.grid(row=1, column=0, columnspan=2, sticky='nsew', padx=12, pady=6)
        frame_central.grid_rowconfigure(0, weight=1)
        frame_central.grid_columnconfigure(0, weight=1)

        self.lb_productos = tk.Listbox(frame_central, font=("Arial", 14))
        self.lb_productos.grid(row=0, column=0, sticky='nsew', padx=6, pady=6)

        # Botones inferiores
        btns = ctk.CTkFrame(self)
        btns.grid(row=2, column=0, columnspan=2, sticky='nsew', padx=12, pady=6)
        btns.grid_columnconfigure(tuple(range(6)), weight=1)

        ctk.CTkButton(btns, text='Agregar producto', command=self.abrir_agregar).grid(row=0, column=0, padx=6, pady=6, sticky='nsew')
        ctk.CTkButton(btns, text='Cargar desde Excel', command=self.cargar_desde_excel).grid(row=0, column=1, padx=6, pady=6, sticky='nsew')
        ctk.CTkButton(btns, text='Modificar producto', command=self.abrir_modificar).grid(row=0, column=2, padx=6, pady=6, sticky='nsew')
        ctk.CTkButton(btns, text='Eliminar producto', command=self.eliminar_producto).grid(row=0, column=3, padx=6, pady=6, sticky='nsew')
        ctk.CTkButton(btns, text='Registrar Venta', command=self.abrir_venta).grid(row=0, column=4, padx=6, pady=6, sticky='nsew')
        ctk.CTkButton(btns, text='Historial de ventas', command=self.abrir_historial).grid(row=0, column=5, padx=6, pady=6, sticky='nsew')

    # ------------------ Tienda selection ------------------
    def _seleccionar_tienda_inicio(self):
        tiendas = self.db.list_tiendas()
        if not tiendas:
            nombre = simpledialog.askstring("Primera tienda", "No hay sucursales. Define el nombre de la primera sucursal:")
            if nombre:
                tid = self.db.add_tienda(nombre)
                self.tienda_id = tid
            else:
                self.destroy(); return
        else:
            # simple selector modal
            dlg = ctk.CTkToplevel(self)
            bring_to_front(self)
            dlg.title("Elegir sucursal")
            dlg.geometry("440x420")
            dlg.transient(self)
            dlg.grab_set()
            frame = ctk.CTkFrame(dlg)
            frame.pack(expand=True, fill='both', padx=12, pady=12)

            ctk.CTkLabel(frame, text='Selecciona sucursal').pack(pady=6)
            lb = tk.Listbox(frame, font=("Segoe UI", 18, "bold"), height=8, activestyle="none")
            lb.pack(expand=True, fill='both', pady=10)

            for t in tiendas:
                lb.insert(tk.END, f"{t['nombre']}")

            def elegir():
                sel = lb.curselection()
                if not sel:
                    return
                text = lb.get(sel[0])
                tid = next(x["id"] for x in tiendas if x["nombre"] == text)
                self.tienda_id = tid
                dlg.destroy()
                self.recargar_pagina()

            def eliminar():
                sel = lb.curselection()
                if not sel:
                    return
                text = lb.get(sel[0])
                tid = next(x["id"] for x in tiendas if x["nombre"] == text)
                if not messagebox.askyesno("Confirmar", f"Eliminar sucursal {text}? Se eliminarán todos sus productos."):
                    return
                # eliminar productos asociados
                prods = self.db.list_productos(tid)
                for p in prods:
                    self.db.delete_producto(p['id'])
                # eliminar tienda
                self.db.cursor.execute("DELETE FROM tiendas WHERE id = ?", (tid,))
                self.db.conn.commit()
                # recargar lista
                lb.delete(0, tk.END)
                tiendas.clear()
                tiendas.extend(self.db.list_tiendas())
                for t in tiendas:
                    lb.insert(tk.END, f"{t['nombre']}")
                # si era la tienda seleccionada, resetear
                if self.tienda_id == tid:
                    self.tienda_id = None

            def agregar():
                nombre = simpledialog.askstring("Nueva sucursal", "Nombre sucursal:")
                if not nombre or nombre.strip() == '':
                    return
                self.db.add_tienda(nombre)
                lb.delete(0, tk.END)
                for t in reversed(self.db.list_tiendas()):
                    lb.insert(tk.END, f"{t['id']} - {t['nombre']}")
            ctk.CTkButton(frame, text='Elegir', command=elegir).pack(side='left', expand=True, padx=6)
            ctk.CTkButton(frame, text='Agregar sucursal', command=agregar).pack(side='right', expand=True, padx=6)
            ctk.CTkButton(frame, text='Eliminar sucursal', command=eliminar).pack(side='right', expand=True, padx=6)
            dlg.wait_window()
        # si tienda ya setea recarga
        if self.tienda_id:
            self.recargar_pagina()

    # ------------------ acciones UI ------------------
    def recargar_pagina(self):
        self.productos = self.db.list_productos(self.tienda_id)
        self._llenar_lista_productos()

    def _llenar_lista_productos(self, filtro=''):
        self.lb_productos.delete(0, tk.END)
        filtro = filtro.lower()
        for p in self.productos:
            detalle = f"{p['nombre']} | stock: {p['stock']} | ${p['precio']}"
            if filtro in detalle.lower():
                self.lb_productos.insert(tk.END, detalle)

    def filtrar_lista(self, event=None):
        texto = self.entry_buscar.get()
        self._llenar_lista_productos(texto)

    def abrir_agregar(self):
        AddEditProductWindow(self, self.db, self.tienda_id, callback=self.recargar_pagina)

    def abrir_modificar(self):
        sel = self.lb_productos.curselection()
        if not sel:
            return
        idx = sel[0]
        p = self.productos[idx]
        AddEditProductWindow(self, self.db, self.tienda_id, producto=p, callback=self.recargar_pagina)

    def eliminar_producto(self):
        sel = self.lb_productos.curselection()
        if not sel:
            return
        idx = sel[0]
        p = self.productos[idx]
        if not messagebox.askyesno("Confirmar", f"Eliminar {p['nombre']}?"):
            return
        self.db.delete_producto(p['id'])
        self.recargar_pagina()

    def abrir_venta(self):
        if not self.productos:
            messagebox.showinfo("Info", "No hay productos cargados")
            return
        SaleWindow(self, self.db, self.productos, refresh_callback=self.recargar_pagina)

    def abrir_historial(self):
        HistoryWindow(self, self.db)

    def cargar_desde_excel(self):
        try:
            df = pd.read_excel('archivo.excel')
            cols = [c.lower() for c in df.columns]
            if not all(col in cols for col in ['nombre', 'stock', 'precio']):
                messagebox.showerror('Error', 'Excel debe contener columnas: nombre, stock, precio (opcional: codigo_barras)')
                return
            for _, row in df.iterrows():
                nombre = str(row['nombre'])
                stock = int(row['stock'])
                precio = float(row['precio'])
                codigo = str(row['codigo_barras']) if 'codigo_barras' in df.columns else None
                try:
                    self.db.add_producto(nombre, stock, precio, self.tienda_id, codigo)
                except sqlite3.IntegrityError:
                    # saltar duplicados
                    continue
            self.recargar_pagina()
            messagebox.showinfo('Éxito', 'Productos cargados desde Excel correctamente')
        except FileNotFoundError:
            messagebox.showerror('Error', 'No se encontró el archivo Control_Huevos_Mayorista.xlsx')
        except Exception as e:
            messagebox.showerror('Error', f'Ocurrió un problema al leer el Excel:\n{e}')

    # ------------------ seguridad (contraseña periódica) ------------------
    def _pedir_contraseña_periodico(self):
        if self.contraseña_ok:
            self.contraseña_ok = False
        # pedir modal
        while True:
            pwd = simpledialog.askstring('Contraseña requerida', 'Introduce la contraseña para continuar:', show='*', parent=self)
            if pwd is None:
                continue
            if pwd == PASSWORD:
                self.contraseña_ok = True
                messagebox.showinfo('Correcto', 'Contraseña correcta. Puedes usar el programa.')
                break
            else:
                messagebox.showerror('Error', 'Contraseña incorrecta. Intenta de nuevo.')
        self.after(INACTIVITY_MS, self._pedir_contraseña_periodico)

    def on_closing(self):
        self.db.close()
        self.destroy()


if __name__ == '__main__':
    app = MainApp()
    app.protocol('WM_DELETE_WINDOW', app.on_closing)
    app.mainloop()
