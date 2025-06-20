import customtkinter as ctk
import sqlite3
from tkinter import messagebox, filedialog
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("energo_control.log"),
                        logging.StreamHandler()
                    ])

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class DatabaseManager:
    def __init__(self, db_name='energo_control.db'):
        self.db_name = db_name
        self.conn = None
        self.init_database()

    def init_database(self):
        try:
            self.conn = sqlite3.connect(self.db_name)
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    location TEXT NOT NULL,
                    affected_consumers TEXT,
                    assigned_brigade TEXT,
                    status TEXT NOT NULL,
                    registration_time TEXT NOT NULL,
                    resolution_time TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS brigades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    specialization TEXT,
                    contact_info TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS equipment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    model TEXT,
                    serial_number TEXT UNIQUE,
                    installation_date TEXT,
                    status TEXT,
                    last_maintenance_date TEXT,
                    location TEXT
                )
            ''')
            self.conn.commit()
            logging.info("Database initialized successfully.")
        except sqlite3.Error as e:
            logging.error(f"Failed to connect to or initialize database: {e}")
            messagebox.showerror("Database Error", f"Failed to connect to or initialize database: {e}")
            self.conn = None

    def get_all_incident_types(self):
        if not self.conn:
            logging.warning("Database not connected when trying to get incident types.")
            return ["Все"]
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT DISTINCT incident_type FROM incidents WHERE incident_type IS NOT NULL AND incident_type != ''")
            types = [row[0] for row in cursor.fetchall()]
            types = sorted(list(set(types)))
            return ["Все"] + types
        except sqlite3.Error as e:
            logging.error(f"Error fetching incident types: {e}")
            messagebox.showerror("Database Error", f"Error fetching incident types: {e}")
            return ["Все"]

    def get_incidents(self, search_query="", status_filter="Все", type_filter="Все", show_active_only=True,
                      sort_column="registration_time", sort_order="DESC"):
        if not self.conn:
            logging.warning("Database not connected when trying to get incidents.")
            return []
        try:
            cursor = self.conn.cursor()
            sql_query = "SELECT id, incident_type, description, location, affected_consumers, assigned_brigade, status, registration_time, resolution_time FROM incidents WHERE 1=1"
            params = []

            if search_query:
                sql_query += " AND (description LIKE ? OR location LIKE ?)"
                params.append(f"%{search_query}%")
                params.append(f"%{search_query}%")

            if status_filter != "Все":
                sql_query += " AND status = ?"
                params.append(status_filter)

            if type_filter != "Все":
                sql_query += " AND incident_type = ?"
                params.append(type_filter)

            if show_active_only:
                sql_query += " AND status != 'Устранено'"

            sql_query += f" ORDER BY {sort_column} {sort_order}"

            cursor.execute(sql_query, tuple(params))
            incidents = cursor.fetchall()
            logging.info(f"Fetched {len(incidents)} incidents with filters.")
            return incidents
        except sqlite3.Error as e:
            logging.error(f"Error fetching incidents from database: {e}")
            messagebox.showerror("Database Error", f"Error fetching incidents: {e}")
            return []

    def save_incident(self, incident_data, incident_id=None):
        if not self.conn:
            logging.warning("Database not connected when trying to save incident.")
            messagebox.showerror("Database Error", "Database not connected.")
            return False

        try:
            cursor = self.conn.cursor()
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if incident_id:
                cursor.execute('''
                    UPDATE incidents SET
                        incident_type=?, description=?, location=?, affected_consumers=?, assigned_brigade=?
                    WHERE id=?
                ''', (incident_data["Тип инцидента"], incident_data["Описание"], incident_data["Местоположение"],
                      incident_data["Затронутые потребители"], incident_data["Назначенная бригада"],
                      incident_id))
                logging.info(f"Incident ID:{incident_id} updated successfully.")
            else:
                cursor.execute('''
                    INSERT INTO incidents (incident_type, description, location, affected_consumers, assigned_brigade, status, registration_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (incident_data["Тип инцидента"], incident_data["Описание"], incident_data["Местоположение"],
                      incident_data["Затронутые потребители"], incident_data["Назначенная бригада"],
                      "Зарегистрирован", current_time))
                incident_id = cursor.lastrowid
                logging.info(f"New incident registered with ID: {incident_id}")

            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"Error saving incident: {e}")
            messagebox.showerror("Database Error", f"Error saving incident: {e}")
            return False

    def get_incident_by_id(self, incident_id):
        if not self.conn:
            logging.warning("Database not connected when trying to get incident by ID.")
            return None
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT incident_type, description, location, affected_consumers, assigned_brigade, status, registration_time, resolution_time FROM incidents WHERE id=?",
                (incident_id,))
            incident = cursor.fetchone()
            return incident
        except sqlite3.Error as e:
            logging.error(f"Error fetching incident ID:{incident_id}: {e}")
            messagebox.showerror("Database Error", f"Error fetching incident: {e}")
            return None

    def delete_incident(self, incident_id):
        if not self.conn:
            logging.warning("Database not connected when trying to delete incident.")
            messagebox.showerror("Database Error", "Database not connected.")
            return False
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM incidents WHERE id=?", (incident_id,))
            self.conn.commit()
            logging.info(f"Incident ID:{incident_id} deleted successfully.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Error deleting incident ID:{incident_id}: {e}")
            messagebox.showerror("Database Error", f"Error deleting incident: {e}")
            return False

    def update_incident_status(self, incident_id, new_status):
        if not self.conn:
            logging.warning("Database not connected when trying to update incident status.")
            messagebox.showerror("Database Error", "Database not connected.")
            return False

        try:
            cursor = self.conn.cursor()
            resolution_time = None

            cursor.execute("SELECT status FROM incidents WHERE id=?", (incident_id,))
            current_status = cursor.fetchone()[0]

            if new_status == "Устранено":
                if current_status == "Устранено":
                    logging.info(f"Incident ID:{incident_id} is already resolved.")
                    messagebox.showinfo("Info", f"Incident ID:{incident_id} is already resolved.")
                    return False
                resolution_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elif new_status == "В работе":
                if current_status == "В работе":
                    logging.info(f"Incident ID:{incident_id} is already in progress.")
                    messagebox.showinfo("Info", f"Incident ID:{incident_id} is already in progress.")
                    return False

            cursor.execute("UPDATE incidents SET status=?, resolution_time=? WHERE id=?",
                           (new_status, resolution_time, incident_id))
            self.conn.commit()
            logging.info(f"Incident ID:{incident_id} status updated to '{new_status}'.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Error updating incident status ID:{incident_id}: {e}")
            messagebox.showerror("Database Error", f"Error updating incident status: {e}")
            return False

    def get_brigades(self, search_query="", sort_column="name", sort_order="ASC"):
        if not self.conn:
            logging.warning("Database not connected when trying to get brigades.")
            return []
        try:
            cursor = self.conn.cursor()
            sql_query = "SELECT id, name, specialization, contact_info FROM brigades WHERE 1=1"
            params = []

            if search_query:
                sql_query += " AND (name LIKE ? OR specialization LIKE ?)"
                params.append(f"%{search_query}%")
                params.append(f"%{search_query}%")

            sql_query += f" ORDER BY {sort_column} {sort_order}"

            cursor.execute(sql_query, tuple(params))
            brigades = cursor.fetchall()
            logging.info(f"Fetched {len(brigades)} brigades with filters.")
            return brigades
        except sqlite3.Error as e:
            logging.error(f"Error fetching brigades from database: {e}")
            messagebox.showerror("Database Error", f"Error fetching brigades: {e}")
            return []

    def save_brigade(self, brigade_data, brigade_id=None):
        if not self.conn:
            logging.warning("Database not connected when trying to save brigade.")
            messagebox.showerror("Database Error", "Database not connected.")
            return False
        try:
            cursor = self.conn.cursor()
            if brigade_id:
                cursor.execute('''
                    UPDATE brigades SET
                        name=?, specialization=?, contact_info=?
                    WHERE id=?
                ''', (brigade_data["Название бригады"], brigade_data["Специализация"], brigade_data["Контактная инфо"],
                      brigade_id))
                logging.info(f"Brigade ID:{brigade_id} updated successfully.")
            else:
                cursor.execute('''
                    INSERT INTO brigades (name, specialization, contact_info)
                    VALUES (?, ?, ?)
                ''', (brigade_data["Название бригады"], brigade_data["Специализация"], brigade_data["Контактная инфо"]))
                brigade_id = cursor.lastrowid
                logging.info(f"New brigade '{brigade_data['Название бригады']}' added with ID: {brigade_id}")

            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            logging.error(f"Brigade with name '{brigade_data['Название бригады']}' already exists.")
            messagebox.showerror("Database Error",
                                 f"Brigade with name '{brigade_data['Название бригады']}' already exists. Brigade name must be unique.")
            return False
        except sqlite3.Error as e:
            logging.error(f"Error saving brigade: {e}")
            messagebox.showerror("Database Error", f"Error saving brigade: {e}")
            return False

    def get_brigade_by_id(self, brigade_id):
        if not self.conn:
            logging.warning("Database not connected when trying to get brigade by ID.")
            return None
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name, specialization, contact_info FROM brigades WHERE id=?", (brigade_id,))
            brigade = cursor.fetchone()
            return brigade
        except sqlite3.Error as e:
            logging.error(f"Error fetching brigade ID:{brigade_id}: {e}")
            messagebox.showerror("Database Error", f"Error fetching brigade: {e}")
            return None

    def delete_brigade(self, brigade_id):
        if not self.conn:
            logging.warning("Database not connected when trying to delete brigade.")
            messagebox.showerror("Database Error", "Database not connected.")
            return False
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM brigades WHERE id=?", (brigade_id,))
            self.conn.commit()
            logging.info(f"Brigade ID:{brigade_id} deleted successfully.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Error deleting brigade ID:{brigade_id}: {e}")
            messagebox.showerror("Database Error", f"Error deleting brigade: {e}")
            return False

    def get_equipment(self, search_query="", sort_column="name", sort_order="ASC"):
        if not self.conn:
            logging.warning("Database not connected when trying to get equipment.")
            return []
        try:
            cursor = self.conn.cursor()
            sql_query = "SELECT id, name, type, model, serial_number, installation_date, status, last_maintenance_date, location FROM equipment WHERE 1=1"
            params = []

            if search_query:
                sql_query += " AND (name LIKE ? OR type LIKE ? OR serial_number LIKE ? OR location LIKE ?)"
                params.append(f"%{search_query}%")
                params.append(f"%{search_query}%")
                params.append(f"%{search_query}%")
                params.append(f"%{search_query}%")

            sql_query += f" ORDER BY {sort_column} {sort_order}"

            cursor.execute(sql_query, tuple(params))
            equipment_list = cursor.fetchall()
            logging.info(f"Fetched {len(equipment_list)} equipment items with filters.")
            return equipment_list
        except sqlite3.Error as e:
            logging.error(f"Error fetching equipment from database: {e}")
            messagebox.showerror("Database Error", f"Error fetching equipment: {e}")
            return []

    def save_equipment(self, equipment_data, equipment_id=None):
        if not self.conn:
            logging.warning("Database not connected when trying to save equipment.")
            messagebox.showerror("Database Error", "Database not connected.")
            return False
        try:
            cursor = self.conn.cursor()
            if equipment_id:
                cursor.execute('''
                    UPDATE equipment SET
                        name=?, type=?, model=?, serial_number=?, installation_date=?, status=?, last_maintenance_date=?, location=?
                    WHERE id=?
                ''', (equipment_data["Название"], equipment_data["Тип"], equipment_data["Модель"],
                      equipment_data["Серийный номер"], equipment_data["Дата установки (ГГГГ-ММ-ДД)"],
                      equipment_data["Статус"], equipment_data["Последнее обслуж. (ГГГГ-ММ-ДД)"],
                      equipment_data["Местоположение"], equipment_id))
                logging.info(f"Equipment ID:{equipment_id} updated successfully.")
            else:
                cursor.execute('''
                    INSERT INTO equipment (name, type, model, serial_number, installation_date, status, last_maintenance_date, location)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (equipment_data["Название"], equipment_data["Тип"], equipment_data["Модель"],
                      equipment_data["Серийный номер"], equipment_data["Дата установки (ГГГГ-ММ-ДД)"],
                      equipment_data["Статус"], equipment_data["Последнее обслуж. (ГГГГ-ММ-ДД)"],
                      equipment_data["Местоположение"]))
                equipment_id = cursor.lastrowid
                logging.info(f"New equipment '{equipment_data['Название']}' added with ID: {equipment_id}")

            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            logging.error(f"Equipment with serial number '{equipment_data['Серийный номер']}' already exists.")
            messagebox.showerror("Database Error",
                                 f"Equipment with serial number '{equipment_data['Серийный номер']}' already exists. Serial number must be unique.")
            return False
        except sqlite3.Error as e:
            logging.error(f"Error saving equipment: {e}")
            messagebox.showerror("Database Error", f"Error saving equipment: {e}")
            return False

    def get_equipment_by_id(self, equipment_id):
        if not self.conn:
            logging.warning("Database not connected when trying to get equipment by ID.")
            return None
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT name, type, model, serial_number, installation_date, status, last_maintenance_date, location FROM equipment WHERE id=?",
                (equipment_id,))
            equipment = cursor.fetchone()
            return equipment
        except sqlite3.Error as e:
            logging.error(f"Error fetching equipment ID:{equipment_id}: {e}")
            messagebox.showerror("Database Error", f"Error fetching equipment: {e}")
            return None

    def delete_equipment(self, equipment_id):
        if not self.conn:
            logging.warning("Database not connected when trying to delete equipment.")
            messagebox.showerror("Database Error", "Database not connected.")
            return False
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM equipment WHERE id=?", (equipment_id,))
            self.conn.commit()
            logging.info(f"Equipment ID:{equipment_id} deleted successfully.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Error deleting equipment ID:{equipment_id}: {e}")
            messagebox.showerror("Database Error", f"Error deleting equipment: {e}")
            return False


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ЭнергоКонтроль: Интеллектуальная Система Управления Сетями")
        self.geometry("1200x800")
        self.resizable(True, True)

        self.configure(fg_color=("#1A1A1A", "#1A1A1A"))

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.db_manager = DatabaseManager()
        if not self.db_manager.conn:
            logging.critical("Application cannot start without database connection.")
            self.destroy()
            return

        self.current_sort_column_incidents = "registration_time"
        self.current_sort_order_incidents = "DESC"

        self.current_sort_column_brigades = "name"
        self.current_sort_order_brigades = "ASC"

        self.current_sort_column_equipment = "name"
        self.current_sort_order_equipment = "ASC"

        self.editing_incident_id = None
        self.save_incident_button = None
        self.cancel_edit_incident_button = None

        self.editing_brigade_id = None
        self.save_brigade_button = None
        self.cancel_edit_brigade_button = None

        self.editing_equipment_id = None
        self.save_equipment_button = None
        self.cancel_edit_equipment_button = None

        self.current_active_report_plot_func = None

        self.navigation_frame = ctk.CTkFrame(self, corner_radius=10,
                                             fg_color=("#2C2C2C", "#2C2C2C"))
        self.navigation_frame.grid(row=0, column=0, rowspan=4, sticky="nsew", padx=10, pady=10)
        self.navigation_frame.grid_rowconfigure(5, weight=1)

        self.navigation_frame_label = ctk.CTkLabel(self.navigation_frame,
                                                   text="⚡ ЭнергоКонтроль ⚡",
                                                   font=ctk.CTkFont(size=25, weight="bold"))
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)

        self.incidents_button = ctk.CTkButton(self.navigation_frame,
                                              text="⚙️ Управление Инцидентами",
                                              corner_radius=10,
                                              height=50,
                                              font=ctk.CTkFont(size=16, weight="bold"),
                                              command=lambda: self.select_frame_by_name("incidents"))
        self.incidents_button.grid(row=1, column=0, sticky="ew", padx=15, pady=8)

        self.reports_button = ctk.CTkButton(self.navigation_frame,
                                            text="📊 Отчеты и Аналитика",
                                            corner_radius=10,
                                            height=50,
                                            font=ctk.CTkFont(size=16, weight="bold"),
                                            command=lambda: self.select_frame_by_name("reports"))
        self.reports_button.grid(row=2, column=0, sticky="ew", padx=15, pady=8)

        self.brigades_button = ctk.CTkButton(self.navigation_frame,
                                             text="🧑‍🔧 Управление Бригадами",
                                             corner_radius=10,
                                             height=50,
                                             font=ctk.CTkFont(size=16, weight="bold"),
                                             command=lambda: self.select_frame_by_name("brigades"))
        self.brigades_button.grid(row=3, column=0, sticky="ew", padx=15, pady=8)

        self.equipment_button = ctk.CTkButton(self.navigation_frame,
                                              text="🔌 Управление Оборудованием",
                                              corner_radius=10,
                                              height=50,
                                              font=ctk.CTkFont(size=16, weight="bold"),
                                              command=lambda: self.select_frame_by_name("equipment"))
        self.equipment_button.grid(row=4, column=0, sticky="ew", padx=15, pady=8)

        self.incident_management_frame = self.create_incident_management_frame()
        self.reports_frame = self.create_reports_frame()
        self.brigade_management_frame = self.create_brigade_management_frame()
        self.equipment_management_frame = self.create_equipment_management_frame()

        self.current_active_frame_name = None
        self.select_frame_by_name("incidents")

    def get_all_incident_types(self):
        return self.db_manager.get_all_incident_types()

    def select_frame_by_name(self, name):
        active_color = ("#4A80B3", "#1E90FF")
        inactive_color = ("gray75", "gray25")

        self.incidents_button.configure(fg_color=active_color if name == "incidents" else inactive_color)
        self.reports_button.configure(fg_color=active_color if name == "reports" else inactive_color)
        self.brigades_button.configure(fg_color=active_color if name == "brigades" else inactive_color)
        self.equipment_button.configure(fg_color=active_color if name == "equipment" else inactive_color)

        self.incident_management_frame.grid_forget()
        self.reports_frame.grid_forget()
        self.brigade_management_frame.grid_forget()
        self.equipment_management_frame.grid_forget()

        if name == "incidents":
            self.incident_management_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
            self.update_incident_type_options()
            self.apply_incident_filters()
            self.current_active_frame_name = "incidents"
        elif name == "reports":
            self.reports_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
            self.draw_default_reports()
            self.current_active_frame_name = "reports"
        elif name == "brigades":
            self.brigade_management_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
            self.apply_brigade_filters()
            self.current_active_frame_name = "brigades"
        elif name == "equipment":
            self.equipment_management_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
            self.apply_equipment_filters()
            self.current_active_frame_name = "equipment"

    def create_incident_management_frame(self):
        frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("#2C2C2C", "#2C2C2C"))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(3, weight=1)

        title_label = ctk.CTkLabel(frame, text="Диспетчеризация Заявок и Управление Авариями",
                                   font=ctk.CTkFont(size=24, weight="bold"), text_color="#E0E0E0")
        title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        registration_frame = ctk.CTkFrame(frame, corner_radius=10, fg_color=("#3C3C3C", "#3C3C3C"), border_width=1,
                                          border_color="#555555")
        registration_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        registration_frame.grid_columnconfigure(1, weight=1)
        registration_frame.grid_columnconfigure(0, weight=0)

        labels_and_placeholders = {
            "Тип инцидента:": "Например, 'Обрыв ЛЭП', 'Короткое замыкание'",
            "Описание:": "Подробное описание инцидента",
            "Местоположение:": "Адрес или координаты",
            "Затронутые потребители:": "Список потребителей или районов",
            "Назначенная бригада:": "Например, 'Бригада 1', 'Иванов А.А.'"
        }
        self.incident_entries = {}

        for i, (label_text, placeholder) in enumerate(labels_and_placeholders.items()):
            label = ctk.CTkLabel(registration_frame, text=label_text, font=ctk.CTkFont(weight="bold"),
                                 text_color="#D0D0D0")
            label.grid(row=i, column=0, padx=20, pady=7, sticky="w")
            entry = ctk.CTkEntry(registration_frame, width=350, placeholder_text=placeholder, corner_radius=8,
                                 height=35)
            entry.grid(row=i, column=1, padx=20, pady=7, sticky="ew")
            self.incident_entries[label_text.replace(":", "").strip()] = entry

        self.incident_entries["status"] = "Зарегистрирован"

        button_row = len(labels_and_placeholders)
        self.save_incident_button = ctk.CTkButton(registration_frame, text="Зарегистрировать Инцидент",
                                                  command=self.save_incident_command, corner_radius=10,
                                                  fg_color="#00A86B", hover_color="#008C5A",
                                                  font=ctk.CTkFont(size=15, weight="bold"), height=40)
        self.save_incident_button.grid(row=button_row, column=0, padx=20, pady=15, sticky="ew")

        self.cancel_edit_incident_button = ctk.CTkButton(registration_frame, text="Очистить/Отмена",
                                                         command=self.cancel_incident_edit_mode, corner_radius=10,
                                                         fg_color="#6C757D", hover_color="#5A6268",
                                                         font=ctk.CTkFont(size=15, weight="bold"), height=40)
        self.cancel_edit_incident_button.grid(row=button_row, column=1, padx=20, pady=15, sticky="ew")

        search_filter_frame = ctk.CTkFrame(frame, corner_radius=10, fg_color=("#3C3C3C", "#3C3C3C"), border_width=1,
                                           border_color="#555555")
        search_filter_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        search_filter_frame.grid_columnconfigure((1, 3, 4), weight=1)

        search_label = ctk.CTkLabel(search_filter_frame, text="🔍 Поиск:", font=ctk.CTkFont(weight="bold"),
                                    text_color="#D0D0D0")
        search_label.grid(row=0, column=0, padx=20, pady=7, sticky="w")
        self.incident_search_entry = ctk.CTkEntry(search_filter_frame, placeholder_text="Описание или Местоположение",
                                                  corner_radius=8, height=30)
        self.incident_search_entry.grid(row=0, column=1, padx=10, pady=7, sticky="ew")
        self.incident_search_entry.bind("<Return>", lambda event: self.apply_incident_filters())

        search_button = ctk.CTkButton(search_filter_frame, text="Найти", command=self.apply_incident_filters,
                                      corner_radius=8, fg_color="#4169E1", hover_color="#1E90FF", height=30)
        search_button.grid(row=0, column=2, padx=10, pady=7)

        status_label = ctk.CTkLabel(search_filter_frame, text="📋 Статус:", font=ctk.CTkFont(weight="bold"),
                                    text_color="#D0D0D0")
        status_label.grid(row=1, column=0, padx=20, pady=7, sticky="w")
        self.status_filter_options = ["Все", "Зарегистрирован", "В работе", "Устранено"]
        self.incident_status_combobox = ctk.CTkComboBox(search_filter_frame, values=self.status_filter_options,
                                                        command=lambda value: self.apply_incident_filters(),
                                                        corner_radius=8, height=30)
        self.incident_status_combobox.set("Все")
        self.incident_status_combobox.grid(row=1, column=1, padx=10, pady=7, sticky="ew")

        type_label = ctk.CTkLabel(search_filter_frame, text="⚡ Тип инцидента:", font=ctk.CTkFont(weight="bold"),
                                  text_color="#D0D0D0")
        type_label.grid(row=0, column=3, padx=20, pady=7, sticky="w")
        self.incident_type_options = self.get_all_incident_types()
        self.incident_type_filter_combobox = ctk.CTkComboBox(search_filter_frame, values=self.incident_type_options,
                                                             command=lambda value: self.apply_incident_filters(),
                                                             corner_radius=8, height=30)
        self.incident_type_filter_combobox.set("Все")
        self.incident_type_filter_combobox.grid(row=0, column=4, padx=10, pady=7, sticky="ew")

        self.show_active_only_var = ctk.BooleanVar(value=True)
        show_active_checkbox = ctk.CTkCheckBox(search_filter_frame, text="Активные инциденты",
                                               command=self.apply_incident_filters,
                                               variable=self.show_active_only_var, font=ctk.CTkFont(size=14),
                                               text_color="#D0D0D0")
        show_active_checkbox.grid(row=1, column=3, padx=20, pady=7, sticky="w")

        reset_filters_button = ctk.CTkButton(search_filter_frame, text="🗑️ Сбросить фильтры",
                                             command=self.reset_incident_filters, corner_radius=8, fg_color="#DC3545",
                                             hover_color="#C82333", height=30)
        reset_filters_button.grid(row=1, column=4, padx=10, pady=7)

        incidents_list_container = ctk.CTkFrame(frame, corner_radius=10, fg_color=("#3C3C3C", "#3C3C3C"),
                                                border_width=1, border_color="#555555")
        incidents_list_container.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        incidents_list_container.grid_columnconfigure(0, weight=1)
        incidents_list_container.grid_rowconfigure(1, weight=1)

        self.incidents_list_scrollable_frame = ctk.CTkScrollableFrame(incidents_list_container, corner_radius=8,
                                                                      fg_color=("#3C3C3C", "#3C3C3C"))
        self.incidents_list_scrollable_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.incidents_list_scrollable_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8), weight=1)

        self.headers_info_incidents = {
            "ID": "id",
            "Тип": "incident_type",
            "Описание": "description",
            "Место": "location",
            "Бригада": "assigned_brigade",
            "Статус": "status",
            "Время рег.": "registration_time",
            "Время устр.": "resolution_time",
            "Действия": None
        }
        self.header_labels_incidents = {}

        for i, header_text in enumerate(self.headers_info_incidents.keys()):
            header_label = ctk.CTkLabel(self.incidents_list_scrollable_frame, text=header_text,
                                        font=ctk.CTkFont(size=14, weight="bold"), text_color="#ADD8E6")
            header_label.grid(row=0, column=i, padx=5, pady=5, sticky="ew")

            self.incidents_list_scrollable_frame.grid_columnconfigure(i, weight=1 if self.headers_info_incidents[
                header_text] else 0)

            db_column = self.headers_info_incidents[header_text]
            if db_column:
                header_label.bind("<Button-1>", lambda event, col=db_column: self.sort_incidents(col))
                self.header_labels_incidents[db_column] = header_label

        export_csv_button = ctk.CTkButton(incidents_list_container, text="📄 Экспорт в CSV",
                                          command=self.export_incidents_to_csv, corner_radius=10,
                                          fg_color="#6C757D", hover_color="#5A6268", font=ctk.CTkFont(weight="bold"))
        export_csv_button.grid(row=0, column=0, padx=15, pady=10, sticky="e")

        self.incident_display_widgets = []

        return frame

    def create_brigade_management_frame(self):
        frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("#2C2C2C", "#2C2C2C"))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        title_label = ctk.CTkLabel(frame, text="🧑‍🔧 Управление Бригадами",
                                   font=ctk.CTkFont(size=24, weight="bold"), text_color="#E0E0E0")
        title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        registration_frame = ctk.CTkFrame(frame, corner_radius=10, fg_color=("#3C3C3C", "#3C3C3C"), border_width=1,
                                          border_color="#555555")
        registration_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        registration_frame.grid_columnconfigure(1, weight=1)
        registration_frame.grid_columnconfigure(0, weight=0)

        labels_and_placeholders = {
            "Название бригады:": "Например, 'Бригада Север', 'Оперативная группа 1'",
            "Специализация:": "Например, 'Высоковольтные сети', 'Подстанции'",
            "Контактная инфо:": "Телефон, Email или ответственное лицо"
        }
        self.brigade_entries = {}

        for i, (label_text, placeholder) in enumerate(labels_and_placeholders.items()):
            label = ctk.CTkLabel(registration_frame, text=label_text, font=ctk.CTkFont(weight="bold"),
                                 text_color="#D0D0D0")
            label.grid(row=i, column=0, padx=20, pady=7, sticky="w")
            entry = ctk.CTkEntry(registration_frame, width=350, placeholder_text=placeholder, corner_radius=8,
                                 height=35)
            entry.grid(row=i, column=1, padx=20, pady=7, sticky="ew")
            self.brigade_entries[label_text.replace(":", "").strip()] = entry

        button_row = len(labels_and_placeholders)
        self.save_brigade_button = ctk.CTkButton(registration_frame, text="Добавить Бригаду",
                                                 command=self.save_brigade_command, corner_radius=10,
                                                 fg_color="#00A86B", hover_color="#008C5A",
                                                 font=ctk.CTkFont(size=15, weight="bold"), height=40)
        self.save_brigade_button.grid(row=button_row, column=0, padx=20, pady=15, sticky="ew")

        self.cancel_edit_brigade_button = ctk.CTkButton(registration_frame, text="Очистить/Отмена",
                                                        command=self.cancel_brigade_edit_mode, corner_radius=10,
                                                        fg_color="#6C757D", hover_color="#5A6268",
                                                        font=ctk.CTkFont(size=15, weight="bold"), height=40)
        self.cancel_edit_brigade_button.grid(row=button_row, column=1, padx=20, pady=15, sticky="ew")

        brigades_list_container = ctk.CTkFrame(frame, corner_radius=10, fg_color=("#3C3C3C", "#3C3C3C"), border_width=1,
                                               border_color="#555555")
        brigades_list_container.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        brigades_list_container.grid_columnconfigure(0, weight=1)
        brigades_list_container.grid_rowconfigure(1, weight=1)

        brigade_search_frame = ctk.CTkFrame(brigades_list_container, fg_color="transparent")
        brigade_search_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        brigade_search_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(brigade_search_frame, text="🔍 Поиск бригад:", font=ctk.CTkFont(weight="bold"),
                     text_color="#D0D0D0").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.brigade_search_entry = ctk.CTkEntry(brigade_search_frame, placeholder_text="Название или специализация",
                                                 corner_radius=8, height=30)
        self.brigade_search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.brigade_search_entry.bind("<Return>", lambda event: self.apply_brigade_filters())
        ctk.CTkButton(brigade_search_frame, text="Найти", command=self.apply_brigade_filters, corner_radius=8,
                      height=30).grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkButton(brigade_search_frame, text="🗑️ Сброс", command=self.reset_brigade_filters, corner_radius=8,
                      fg_color="#DC3545", hover_color="#C82333", height=30).grid(row=0, column=3, padx=5, pady=5)

        self.brigades_list_scrollable_frame = ctk.CTkScrollableFrame(brigades_list_container, corner_radius=8,
                                                                     fg_color=("#3C3C3C", "#3C3C3C"))
        self.brigades_list_scrollable_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.brigades_list_scrollable_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.headers_info_brigades = {
            "ID": "id",
            "Название": "name",
            "Специализация": "specialization",
            "Контакты": "contact_info",
            "Действия": None
        }
        self.header_labels_brigades = {}

        for i, header_text in enumerate(self.headers_info_brigades.keys()):
            header_label = ctk.CTkLabel(self.brigades_list_scrollable_frame, text=header_text,
                                        font=ctk.CTkFont(size=14, weight="bold"), text_color="#ADD8E6")
            header_label.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            self.brigades_list_scrollable_frame.grid_columnconfigure(i, weight=1 if self.headers_info_brigades[
                header_text] else 0)

            db_column = self.headers_info_brigades[header_text]
            if db_column:
                header_label.bind("<Button-1>", lambda event, col=db_column: self.sort_brigades(col))
                self.header_labels_brigades[db_column] = header_label

        self.brigade_display_widgets = []

        return frame

    def create_equipment_management_frame(self):
        frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("#2C2C2C", "#2C2C2C"))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        title_label = ctk.CTkLabel(frame, text="🔌 Управление Оборудованием",
                                   font=ctk.CTkFont(size=24, weight="bold"), text_color="#E0E0E0")
        title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        registration_frame = ctk.CTkFrame(frame, corner_radius=10, fg_color=("#3C3C3C", "#3C3C3C"), border_width=1,
                                          border_color="#555555")
        registration_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        registration_frame.grid_columnconfigure(1, weight=1)
        registration_frame.grid_columnconfigure(0, weight=0)

        labels_and_placeholders = {
            "Название:": "Например, 'Трансформатор ТМ-100'",
            "Тип:": "Например, 'Трансформатор', 'Линия', 'Выключатель'",
            "Модель:": "Модель оборудования",
            "Серийный номер:": "Уникальный серийный номер",
            "Дата установки (ГГГГ-ММ-ДД):": "Формат ГГГГ-ММ-ДД",
            "Статус:": "Рабочий, В ремонте, Выведен",
            "Последнее обслуж. (ГГГГ-ММ-ДД):": "Формат ГГГГ-ММ-ДД",
            "Местоположение:": "Подстанция 'Южная', Опора №5"
        }
        self.equipment_entries = {}

        for i, (label_text, placeholder) in enumerate(labels_and_placeholders.items()):
            label = ctk.CTkLabel(registration_frame, text=label_text, font=ctk.CTkFont(weight="bold"),
                                 text_color="#D0D0D0")
            label.grid(row=i, column=0, padx=20, pady=7, sticky="w")
            entry = ctk.CTkEntry(registration_frame, width=350, placeholder_text=placeholder, corner_radius=8,
                                 height=35)
            entry.grid(row=i, column=1, padx=20, pady=7, sticky="ew")
            self.equipment_entries[label_text.replace(":", "").strip()] = entry

        button_row = len(labels_and_placeholders)
        self.save_equipment_button = ctk.CTkButton(registration_frame, text="Добавить Оборудование",
                                                   command=self.save_equipment_command, corner_radius=10,
                                                   fg_color="#00A86B", hover_color="#008C5A",
                                                   font=ctk.CTkFont(size=15, weight="bold"), height=40)
        self.save_equipment_button.grid(row=button_row, column=0, padx=20, pady=15, sticky="ew")

        self.cancel_edit_equipment_button = ctk.CTkButton(registration_frame, text="Очистить/Отмена",
                                                          command=self.cancel_equipment_edit_mode, corner_radius=10,
                                                          fg_color="#6C757D", hover_color="#5A6268",
                                                          font=ctk.CTkFont(size=15, weight="bold"), height=40)
        self.cancel_edit_equipment_button.grid(row=button_row, column=1, padx=20, pady=15, sticky="ew")

        equipment_list_container = ctk.CTkFrame(frame, corner_radius=10, fg_color=("#3C3C3C", "#3C3C3C"),
                                                border_width=1, border_color="#555555")
        equipment_list_container.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        equipment_list_container.grid_columnconfigure(0, weight=1)
        equipment_list_container.grid_rowconfigure(1, weight=1)

        equipment_search_frame = ctk.CTkFrame(equipment_list_container, fg_color="transparent")
        equipment_search_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        equipment_search_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(equipment_search_frame, text="🔍 Поиск оборудования:", font=ctk.CTkFont(weight="bold"),
                     text_color="#D0D0D0").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.equipment_search_entry = ctk.CTkEntry(equipment_search_frame,
                                                   placeholder_text="Название, тип или серийный номер", corner_radius=8,
                                                   height=30)
        self.equipment_search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.equipment_search_entry.bind("<Return>", lambda event: self.apply_equipment_filters())
        ctk.CTkButton(equipment_search_frame, text="Найти", command=self.apply_equipment_filters, corner_radius=8,
                      height=30).grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkButton(equipment_search_frame, text="🗑️ Сброс", command=self.reset_equipment_filters, corner_radius=8,
                      fg_color="#DC3545", hover_color="#C82333", height=30).grid(row=0, column=3, padx=5, pady=5)

        self.equipment_list_scrollable_frame = ctk.CTkScrollableFrame(equipment_list_container, corner_radius=8,
                                                                      fg_color=("#3C3C3C", "#3C3C3C"))
        self.equipment_list_scrollable_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.equipment_list_scrollable_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8), weight=1)

        self.headers_info_equipment = {
            "ID": "id",
            "Название": "name",
            "Тип": "type",
            "Модель": "model",
            "Сер. номер": "serial_number",
            "Установлен": "installation_date",
            "Статус": "status",
            "Послед. обслуж.": "last_maintenance_date",
            "Место": "location",
            "Действия": None
        }
        self.header_labels_equipment = {}

        for i, header_text in enumerate(self.headers_info_equipment.keys()):
            header_label = ctk.CTkLabel(self.equipment_list_scrollable_frame, text=header_text,
                                        font=ctk.CTkFont(size=14, weight="bold"), text_color="#ADD8E6")
            header_label.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            self.equipment_list_scrollable_frame.grid_columnconfigure(i, weight=1 if self.headers_info_equipment[
                header_text] else 0)

            db_column = self.headers_info_equipment[header_text]
            if db_column:
                header_label.bind("<Button-1>", lambda event, col=db_column: self.sort_equipment(col))
                self.header_labels_equipment[db_column] = header_label

        self.equipment_display_widgets = []

        return frame

    def create_reports_frame(self):
        frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("#2C2C2C", "#2C2C2C"))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        title_label = ctk.CTkLabel(frame, text="📊 Отчеты и Аналитика Инцидентов",
                                   font=ctk.CTkFont(size=24, weight="bold"), text_color="#E0E0E0")
        title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        report_controls_frame = ctk.CTkFrame(frame, corner_radius=10, fg_color=("#3C3C3C", "#3C3C3C"), border_width=1,
                                             border_color="#555555")
        report_controls_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        report_controls_frame.grid_columnconfigure((1, 3, 5), weight=1)

        ctk.CTkLabel(report_controls_frame, text="Начальная дата (ГГГГ-ММ-ДД):", font=ctk.CTkFont(weight="bold"),
                     text_color="#D0D0D0").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.start_date_entry = ctk.CTkEntry(report_controls_frame, placeholder_text="2023-01-01", corner_radius=8,
                                             height=30)
        self.start_date_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(report_controls_frame, text="Конечная дата (ГГГГ-ММ-ДД):", font=ctk.CTkFont(weight="bold"),
                     text_color="#D0D0D0").grid(row=0, column=2, padx=10, pady=5, sticky="w")
        self.end_date_entry = ctk.CTkEntry(report_controls_frame,
                                           placeholder_text=datetime.date.today().strftime("%Y-%m-%d"), corner_radius=8,
                                           height=30)
        self.end_date_entry.grid(row=0, column=3, padx=10, pady=5, sticky="ew")

        ctk.CTkButton(report_controls_frame, text="Применить даты", command=self.apply_report_date_filters,
                      corner_radius=8, fg_color="#4169E1", hover_color="#1E90FF").grid(row=0, column=4, padx=10, pady=5)
        ctk.CTkButton(report_controls_frame, text="Сбросить даты", command=self.reset_report_date_filters,
                      corner_radius=8, fg_color="#6C757D", hover_color="#5A6268").grid(row=0, column=5, padx=10, pady=5)

        report_buttons_frame = ctk.CTkFrame(report_controls_frame, fg_color="transparent")
        report_buttons_frame.grid(row=1, column=0, columnspan=6, padx=10, pady=10, sticky="ew")
        report_buttons_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        ctk.CTkButton(report_buttons_frame, text="📊 Инциденты по типу", command=self.plot_incidents_by_type,
                      corner_radius=10, font=ctk.CTkFont(size=15, weight="bold"), height=40).grid(row=0, column=0,
                                                                                                  padx=5, pady=5,
                                                                                                  sticky="ew")
        ctk.CTkButton(report_buttons_frame, text="📉 Инциденты по статусу", command=self.plot_incidents_by_status,
                      corner_radius=10, font=ctk.CTkFont(size=15, weight="bold"), height=40).grid(row=0, column=1,
                                                                                                  padx=5, pady=5,
                                                                                                  sticky="ew")
        ctk.CTkButton(report_buttons_frame, text="📈 Инциденты по времени", command=self.plot_incidents_over_time,
                      corner_radius=10, font=ctk.CTkFont(size=15, weight="bold"), height=40).grid(row=0, column=2,
                                                                                                  padx=5, pady=5,
                                                                                                  sticky="ew")
        ctk.CTkButton(report_buttons_frame, text="🧑‍🔧 Инциденты по бригадам", command=self.plot_incidents_by_brigade,
                      corner_radius=10, font=ctk.CTkFont(size=15, weight="bold"), height=40).grid(row=0, column=3,
                                                                                                  padx=5, pady=5,
                                                                                                  sticky="ew")
        ctk.CTkButton(report_buttons_frame, text="⏳ Время устранения", command=self.plot_incident_resolution_time,
                      corner_radius=10, font=ctk.CTkFont(size=15, weight="bold"), height=40).grid(row=0, column=4,
                                                                                                  padx=5, pady=5,
                                                                                                  sticky="ew")

        self.chart_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.chart_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=20, pady=10)
        self.chart_frame.grid_columnconfigure(0, weight=1)
        self.chart_frame.grid_rowconfigure(0, weight=1)

        return frame

    def draw_plot(self, fig):
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side=ctk.TOP, fill=ctk.BOTH, expand=True)
        canvas.draw()
        plt.close(fig)

    def get_incidents_data_for_reports(self, start_date=None, end_date=None):
        data_raw = self.db_manager.get_incidents(
            sort_column="registration_time",
            sort_order="ASC",
            search_query="",
            status_filter="Все",
            type_filter="Все",
            show_active_only=False
        )

        filtered_data = []
        for row in data_raw:
            reg_time_str = row[7]
            reg_date = datetime.datetime.strptime(reg_time_str, "%Y-%m-%d %H:%M:%S").date()

            if start_date:
                try:
                    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
                    if reg_date < start_dt:
                        continue
                except ValueError:
                    messagebox.showwarning("Invalid Date Format", "Start date must be in YYYY-MM-DD format.")
                    return []

            if end_date:
                try:
                    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
                    if reg_date > end_dt:
                        continue
                except ValueError:
                    messagebox.showwarning("Invalid Date Format", "End date must be in YYYY-MM-DD format.")
                    return []
            filtered_data.append(row)
        return filtered_data

    def apply_report_date_filters(self):
        if self.current_active_report_plot_func:
            self.current_active_report_plot_func()
        else:
            self.draw_default_reports()

    def reset_report_date_filters(self):
        self.start_date_entry.delete(0, ctk.END)
        self.end_date_entry.delete(0, ctk.END)
        self.end_date_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        self.apply_report_date_filters()

    def plot_incidents_by_type(self):
        self.current_active_report_plot_func = self.plot_incidents_by_type
        start_date = self.start_date_entry.get().strip() or None
        end_date = self.end_date_entry.get().strip() or None

        data_raw = self.get_incidents_data_for_reports(start_date, end_date)

        if not data_raw:
            messagebox.showinfo("No Data",
                                "No data to plot incidents by type for the selected period.")
            return

        type_counts = {}
        for row in data_raw:
            inc_type = row[1]
            type_counts[inc_type] = type_counts.get(inc_type, 0) + 1

        types = list(type_counts.keys())
        counts = list(type_counts.values())

        fig, ax = plt.subplots(figsize=(8, 6), facecolor="#2C2C2C")
        ax.bar(types, counts, color="#4169E1")
        ax.set_title(
            'Количество Инцидентов по Типу' + (f'\n({start_date} - {end_date})' if start_date or end_date else ''),
            color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], fontsize=16, weight='bold')
        ax.set_xlabel('Тип Инцидента', color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], fontsize=12)
        ax.set_ylabel('Количество', color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], fontsize=12)
        ax.tick_params(axis='x', rotation=45, labelcolor=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1],
                       labelsize=10)
        ax.tick_params(axis='y', labelcolor=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], labelsize=10)
        ax.set_facecolor("#2C2C2C")
        ax.spines['bottom'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.spines['top'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.spines['right'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.spines['left'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.tick_params(axis='x', colors=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.tick_params(axis='y', colors=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        plt.tight_layout()

        self.draw_plot(fig)

    def plot_incidents_by_status(self):
        self.current_active_report_plot_func = self.plot_incidents_by_status
        start_date = self.start_date_entry.get().strip() or None
        end_date = self.end_date_entry.get().strip() or None

        data_raw = self.get_incidents_data_for_reports(start_date, end_date)

        if not data_raw:
            messagebox.showinfo("No Data",
                                "No data to plot incidents by status for the selected period.")
            return

        status_counts = {}
        for row in data_raw:
            status = row[6]
            status_counts[status] = status_counts.get(status, 0) + 1

        statuses = list(status_counts.keys())
        counts = list(status_counts.values())

        colors = []
        for status in statuses:
            if status == "Зарегистрирован":
                colors.append("#FF6347")
            elif status == "В работе":
                colors.append("#FFD700")
            elif status == "Устранено":
                colors.append("#32CD32")
            else:
                colors.append("#A9A9A9")

        fig, ax = plt.subplots(figsize=(8, 6), facecolor="#2C2C2C")
        ax.pie(counts, labels=statuses, autopct='%1.1f%%', startangle=90, colors=colors,
               textprops={'color': ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], 'fontsize': 11,
                          'weight': 'bold'})
        ax.set_title('Распределение Инцидентов по Статусу' + (
            f'\n({start_date} - {end_date})' if start_date or end_date else ''),
                     color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], fontsize=16, weight='bold')
        ax.axis('equal')
        ax.set_facecolor("#2C2C2C")

        self.draw_plot(fig)

    def plot_incidents_over_time(self):
        self.current_active_report_plot_func = self.plot_incidents_over_time
        start_date = self.start_date_entry.get().strip() or None
        end_date = self.end_date_entry.get().strip() or None

        data_raw = self.get_incidents_data_for_reports(start_date, end_date)

        if not data_raw:
            messagebox.showinfo("No Data",
                                "No data to plot incidents over time for the selected period.")
            return

        date_counts = {}
        for row in data_raw:
            reg_time = row[7]
            reg_date = reg_time.split(" ")[0]
            date_counts[reg_date] = date_counts.get(reg_date, 0) + 1

        dates = sorted(date_counts.keys())
        counts = [date_counts[d] for d in dates]

        fig, ax = plt.subplots(figsize=(10, 6), facecolor="#2C2C2C")
        ax.plot(dates, counts, marker='o', color="#FF6347", linewidth=2)
        ax.set_title('Количество Зарегистрированных Инцидентов по Датам' + (
            f'\n({start_date} - {end_date})' if start_date or end_date else ''),
                     color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], fontsize=16, weight='bold')
        ax.set_xlabel('Дата Регистрации', color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], fontsize=12)
        ax.set_ylabel('Количество Инцидентов', color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], fontsize=12)
        ax.tick_params(axis='x', rotation=45, labelcolor=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1],
                       labelsize=10)
        ax.tick_params(axis='y', labelcolor=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], labelsize=10)
        ax.grid(True, linestyle='--', alpha=0.6, color="#555555")
        ax.set_facecolor("#2C2C2C")
        ax.spines['bottom'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.spines['top'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.spines['right'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.spines['left'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.tick_params(axis='x', colors=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.tick_params(axis='y', colors=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        plt.tight_layout()

        self.draw_plot(fig)

    def plot_incidents_by_brigade(self):
        self.current_active_report_plot_func = self.plot_incidents_by_brigade
        start_date = self.start_date_entry.get().strip() or None
        end_date = self.end_date_entry.get().strip() or None

        data_raw = self.get_incidents_data_for_reports(start_date, end_date)

        if not data_raw:
            messagebox.showinfo("No Data",
                                "No data to plot incidents by brigades for the selected period.")
            return

        brigade_counts = {}
        for row in data_raw:
            brigade = row[5] if row[5] else "Не назначена"
            brigade_counts[brigade] = brigade_counts.get(brigade, 0) + 1

        brigades = list(brigade_counts.keys())
        counts = list(brigade_counts.values())

        fig, ax = plt.subplots(figsize=(8, 6), facecolor="#2C2C2C")
        ax.bar(brigades, counts, color="#007BFF")
        ax.set_title(
            'Количество Инцидентов по Бригадам' + (f'\n({start_date} - {end_date})' if start_date or end_date else ''),
            color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], fontsize=16, weight='bold')
        ax.set_xlabel('Назначенная Бригада', color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], fontsize=12)
        ax.set_ylabel('Количество', color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], fontsize=12)
        ax.tick_params(axis='x', rotation=45, labelcolor=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1],
                       labelsize=10)
        ax.tick_params(axis='y', labelcolor=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], labelsize=10)
        ax.set_facecolor("#2C2C2C")
        ax.spines['bottom'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.spines['top'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.spines['right'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.spines['left'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.tick_params(axis='x', colors=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.tick_params(axis='y', colors=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        plt.tight_layout()

        self.draw_plot(fig)

    def plot_incident_resolution_time(self):
        self.current_active_report_plot_func = self.plot_incident_resolution_time
        start_date = self.start_date_entry.get().strip() or None
        end_date = self.end_date_entry.get().strip() or None

        data_raw = self.get_incidents_data_for_reports(start_date, end_date)

        if not data_raw:
            messagebox.showinfo("No Data",
                                "No data to plot incident resolution time for the selected period.")
            return

        resolution_times_seconds = []
        for row in data_raw:
            reg_time_str = row[7]
            res_time_str = row[8]

            if res_time_str and reg_time_str:
                try:
                    reg_dt = datetime.datetime.strptime(reg_time_str, "%Y-%m-%d %H:%M:%S")
                    res_dt = datetime.datetime.strptime(res_time_str, "%Y-%m-%d %H:%M:%S")
                    time_diff = res_dt - reg_dt
                    resolution_times_seconds.append(time_diff.total_seconds())
                except ValueError:
                    logging.warning(f"Could not parse datetime for incident resolution: {reg_time_str}, {res_time_str}")
                    continue

        if not resolution_times_seconds:
            messagebox.showinfo("No Data",
                                "No resolved incidents with valid dates for resolution time calculation.")
            return

        resolution_times_hours = [t / 3600 for t in resolution_times_seconds]

        fig, ax = plt.subplots(figsize=(10, 6), facecolor="#2C2C2C")

        ax.hist(resolution_times_hours, bins=20, color="#28A745", edgecolor="#3C3C3C", linewidth=1.2)
        ax.set_title('Распределение Времени Устранения Инцидентов (Часы)' + (
            f'\n({start_date} - {end_date})' if start_date or end_date else ''),
                     color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], fontsize=16, weight='bold')
        ax.set_xlabel('Время Устранения (Часы)', color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], fontsize=12)
        ax.set_ylabel('Количество Инцидентов', color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], fontsize=12)
        ax.tick_params(axis='x', labelcolor=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], labelsize=10)
        ax.tick_params(axis='y', labelcolor=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1], labelsize=10)
        ax.set_facecolor("#2C2C2C")
        ax.spines['bottom'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.spines['top'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.spines['right'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.spines['left'].set_color(ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.tick_params(axis='x', colors=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.tick_params(axis='y', colors=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1])
        ax.grid(True, linestyle='--', alpha=0.6, color="#555555")
        plt.tight_layout()

        self.draw_plot(fig)

    def draw_default_reports(self):
        self.current_active_report_plot_func = self.plot_incidents_by_type
        self.plot_incidents_by_type()

    def clear_incident_form(self):
        for key, entry in self.incident_entries.items():
            if isinstance(entry, ctk.CTkEntry):
                entry.delete(0, ctk.END)
        self.editing_incident_id = None
        self.save_incident_button.configure(text="Зарегистрировать Инцидент", fg_color="#00A86B", hover_color="#008C5A")
        self.cancel_edit_incident_button.configure(text="Очистить/Отмена", fg_color="#6C757D", hover_color="#5A6268")

    def save_incident_command(self):
        incident_data = {key: entry.get() if isinstance(entry, ctk.CTkEntry) else entry
                         for key, entry in self.incident_entries.items()}

        if not incident_data["Тип инцидента"] or not incident_data["Описание"] or not incident_data["Местоположение"]:
            messagebox.showwarning("Input Error", "Type, Description, and Location are mandatory fields.")
            logging.warning("Attempted to save incident with missing mandatory fields.")
            return

        success = self.db_manager.save_incident(incident_data, self.editing_incident_id)
        if success:
            messagebox.showinfo("Success", f"Incident successfully {'updated' if self.editing_incident_id else 'registered'}.")
            self.clear_incident_form()
            self.update_incident_type_options()
            self.apply_incident_filters()

    def edit_incident(self, incident_id):
        incident = self.db_manager.get_incident_by_id(incident_id)

        if incident:
            self.incident_entries["Тип инцидента"].delete(0, ctk.END)
            self.incident_entries["Тип инцидента"].insert(0, incident[0])
            self.incident_entries["Описание"].delete(0, ctk.END)
            self.incident_entries["Описание"].insert(0, incident[1])
            self.incident_entries["Местоположение"].delete(0, ctk.END)
            self.incident_entries["Местоположение"].insert(0, incident[2])
            self.incident_entries["Затронутые потребители"].delete(0, ctk.END)
            self.incident_entries["Затронутые потребители"].insert(0, incident[3] if incident[3] else "")
            self.incident_entries["Назначенная бригада"].delete(0, ctk.END)
            self.incident_entries["Назначенная бригада"].insert(0, incident[4] if incident[4] else "")

            self.editing_incident_id = incident_id
            self.save_incident_button.configure(text="Обновить Инцидент", fg_color="#007BFF", hover_color="#0056B3")
            self.cancel_edit_incident_button.configure(text="Отмена", fg_color="red", hover_color="darkred")
        else:
            messagebox.showwarning("Error", "Incident not found.")
            logging.warning(f"Attempted to edit non-existent incident ID:{incident_id}")

    def delete_incident(self, incident_id):
        confirm = messagebox.askyesno("Confirm Deletion",
                                      f"Are you sure you want to delete incident ID:{incident_id}?")
        if confirm:
            success = self.db_manager.delete_incident(incident_id)
            if success:
                messagebox.showinfo("Success", f"Incident ID:{incident_id} successfully deleted.")
                self.update_incident_type_options()
                self.apply_incident_filters()
                if self.editing_incident_id == incident_id:
                    self.cancel_incident_edit_mode()

    def export_incidents_to_csv(self):
        search_query = self.incident_search_entry.get().strip()
        status_filter = self.incident_status_combobox.get()
        type_filter = self.incident_type_filter_combobox.get()
        show_active_only = self.show_active_only_var.get()
        sort_column = self.current_sort_column_incidents
        sort_order = self.current_sort_order_incidents

        incidents = self.db_manager.get_incidents(
            search_query, status_filter, type_filter, show_active_only, sort_column, sort_order
        )

        if not incidents:
            messagebox.showinfo("No Data", "No incidents to export to CSV with current filters.")
            logging.info("No incidents found for CSV export with current filters.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                 filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                                                 title="Save Incidents as CSV")
        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)

                headers = ["ID", "Тип Инцидента", "Описание", "Местоположение", "Затронутые Потребители",
                           "Назначенная Бригада", "Статус", "Время Регистрации", "Время Устранения"]
                csv_writer.writerow(headers)

                csv_writer.writerows(incidents)

            messagebox.showinfo("Export Complete", f"Incidents successfully exported to:\n{file_path}")
            logging.info(f"Incidents exported to {file_path}")
        except Exception as e:
            logging.error(f"Error during CSV export: {e}")
            messagebox.showerror("Export Error", f"An unexpected error occurred during export: {e}")

    def cancel_incident_edit_mode(self):
        self.editing_incident_id = None
        self.clear_incident_form()

    def update_incident_type_options(self):
        current_types = self.get_all_incident_types()
        self.incident_type_filter_combobox.configure(values=current_types)
        if self.incident_type_filter_combobox.get() not in current_types:
            self.incident_type_filter_combobox.set("Все")

    def apply_incident_filters(self):
        search_query = self.incident_search_entry.get().strip()
        status_filter = self.incident_status_combobox.get()
        type_filter = self.incident_type_filter_combobox.get()
        show_active_only = self.show_active_only_var.get()

        self.load_incidents_to_display(search_query, status_filter, type_filter, show_active_only,
                                       self.current_sort_column_incidents, self.current_sort_order_incidents)

    def reset_incident_filters(self):
        self.incident_search_entry.delete(0, ctk.END)
        self.incident_status_combobox.set("Все")
        self.incident_type_filter_combobox.set("Все")
        self.show_active_only_var.set(True)
        self.current_sort_column_incidents = "registration_time"
        self.current_sort_order_incidents = "DESC"
        self.apply_incident_filters()

    def sort_incidents(self, column_name):
        if self.current_sort_column_incidents == column_name:
            self.current_sort_order_incidents = "ASC" if self.current_sort_order_incidents == "DESC" else "DESC"
        else:
            self.current_sort_column_incidents = column_name
            self.current_sort_order_incidents = "ASC"
        self.apply_incident_filters()

    def load_incidents_to_display(self, search_query="", status_filter="Все", type_filter="Все", show_active_only=True,
                                  sort_column="registration_time", sort_order="DESC"):
        incidents = self.db_manager.get_incidents(search_query, status_filter, type_filter, show_active_only,
                                                  sort_column, sort_order)

        for widget in self.incident_display_widgets:
            widget.destroy()
        self.incident_display_widgets.clear()

        for db_col, label in self.header_labels_incidents.items():
            display_text = ""
            for k, v in self.headers_info_incidents.items():
                if v == db_col:
                    display_text = k
                    break

            if db_col == sort_column:
                arrow = " ▲" if sort_order == "ASC" else " ▼"
                label.configure(text=f"{display_text}{arrow}")
            else:
                label.configure(text=display_text)

        current_row = 1
        row_colors = ("#343638", "#2b2b2b") if ctk.get_appearance_mode() == "Dark" else ("#ebebeb", "#e0e0e0")

        if not incidents:
            no_incidents_label = ctk.CTkLabel(self.incidents_list_scrollable_frame,
                                              text="No registered incidents matching the selected filters.",
                                              font=ctk.CTkFont(size=14, slant="italic"))
            no_incidents_label.grid(row=current_row, column=0, columnspan=len(self.headers_info_incidents), padx=20,
                                    pady=20)
            self.incident_display_widgets.append(no_incidents_label)
            return

        for incident in incidents:
            incident_id, inc_type, desc, loc, affected_consumers, brigade, status, reg_time, res_time = incident

            base_row_color = row_colors[current_row % 2]
            bg_color = base_row_color
            if status == "Зарегистрирован":
                bg_color = "#FF6347"
            elif status == "В работе":
                bg_color = "#FFD700"
            elif status == "Устранено":
                bg_color = "#32CD32"
            else:
                bg_color = "#A9A9A9"

            display_data = [
                str(incident_id),
                inc_type,
                desc,
                loc,
                brigade if brigade else "-",
                status,
                reg_time,
                res_time if res_time else "-"
            ]

            for col_idx, data_item in enumerate(display_data):
                label = ctk.CTkLabel(self.incidents_list_scrollable_frame, text=data_item, wraplength=120,
                                     fg_color=bg_color, corner_radius=0)
                label.grid(row=current_row, column=col_idx, padx=1, pady=1, sticky="nsew")
                self.incident_display_widgets.append(label)

            actions_frame = ctk.CTkFrame(self.incidents_list_scrollable_frame, fg_color="transparent")
            actions_frame.grid(row=current_row, column=len(display_data), columnspan=2, padx=2, pady=1, sticky="ew")
            actions_frame.grid_columnconfigure((0, 1), weight=1)

            edit_button = ctk.CTkButton(actions_frame, text="Редактировать",
                                        command=lambda i_id=incident_id: self.edit_incident(i_id),
                                        corner_radius=6, width=90, fg_color="#36719F", hover_color="#4A80B3")
            edit_button.grid(row=0, column=0, padx=1, pady=1, sticky="ew")
            self.incident_display_widgets.append(edit_button)

            delete_button = ctk.CTkButton(actions_frame, text="Удалить",
                                          command=lambda i_id=incident_id: self.delete_incident(i_id),
                                          corner_radius=6, width=90, fg_color="red", hover_color="darkred")
            delete_button.grid(row=0, column=1, padx=1, pady=1, sticky="ew")
            self.incident_display_widgets.append(delete_button)

            status_in_progress_button = ctk.CTkButton(actions_frame, text="В работе",
                                                      command=lambda i_id=incident_id: self.update_incident_status_command(
                                                          i_id, "В работе"),
                                                      corner_radius=6, width=90, fg_color="#4169E1",
                                                      hover_color="#1E90FF")
            status_in_progress_button.grid(row=1, column=0, padx=1, pady=1, sticky="ew")
            self.incident_display_widgets.append(status_in_progress_button)

            status_resolved_button = ctk.CTkButton(actions_frame, text="Устранено",
                                                   command=lambda i_id=incident_id: self.update_incident_status_command(
                                                       i_id, "Устранено"),
                                                   corner_radius=6, width=90, fg_color="#228B22",
                                                   hover_color="#3CB371")
            status_resolved_button.grid(row=1, column=1, padx=1, pady=1, sticky="ew")
            self.incident_display_widgets.append(status_resolved_button)

            self.incident_display_widgets.append(actions_frame)

            if status == "Устранено":
                edit_button.configure(state="disabled", fg_color="gray", text_color="lightgray")
                delete_button.configure(state="normal", fg_color="red", hover_color="darkred")
                status_in_progress_button.configure(state="disabled", fg_color="gray", text_color="lightgray")
                status_resolved_button.configure(state="disabled", fg_color="gray", text_color="lightgray")
            elif status == "В работе":
                edit_button.configure(state="normal", fg_color="#36719F", hover_color="#4A80B3")
                delete_button.configure(state="normal", fg_color="red", hover_color="darkred")
                status_in_progress_button.configure(state="disabled", fg_color="gray", text_color="lightgray")
                status_resolved_button.configure(state="normal", fg_color="#228B22", hover_color="#3CB371")
            elif status == "Зарегистрирован":
                edit_button.configure(state="normal", fg_color="#36719F", hover_color="#4A80B3")
                delete_button.configure(state="normal", fg_color="red", hover_color="darkred")
                status_in_progress_button.configure(state="normal", fg_color="#4169E1", hover_color="#1E90FF")
                status_resolved_button.configure(state="normal", fg_color="#228B22", hover_color="#3CB371")

            current_row += 1

    def update_incident_status_command(self, incident_id, new_status):
        success = self.db_manager.update_incident_status(incident_id, new_status)
        if success:
            self.update_incident_type_options()
            self.apply_incident_filters()

    def clear_brigade_form(self):
        for key, entry in self.brigade_entries.items():
            if isinstance(entry, ctk.CTkEntry):
                entry.delete(0, ctk.END)
        self.editing_brigade_id = None
        self.save_brigade_button.configure(text="Добавить Бригаду", fg_color="#00A86B", hover_color="#008C5A")
        self.cancel_edit_brigade_button.configure(text="Очистить/Отмена", fg_color="#6C757D", hover_color="#5A6268")

    def save_brigade_command(self):
        brigade_data = {key: entry.get() for key, entry in self.brigade_entries.items()}

        if not brigade_data["Название бригады"]:
            messagebox.showwarning("Input Error", "Brigade name is a mandatory field.")
            logging.warning("Attempted to save brigade with missing name.")
            return

        success = self.db_manager.save_brigade(brigade_data, self.editing_brigade_id)
        if success:
            messagebox.showinfo("Success", f"Brigade successfully {'updated' if self.editing_brigade_id else 'added'}.")
            self.clear_brigade_form()
            self.apply_brigade_filters()

    def edit_brigade(self, brigade_id):
        brigade = self.db_manager.get_brigade_by_id(brigade_id)

        if brigade:
            self.brigade_entries["Название бригады"].delete(0, ctk.END)
            self.brigade_entries["Название бригады"].insert(0, brigade[0])
            self.brigade_entries["Специализация"].delete(0, ctk.END)
            self.brigade_entries["Специализация"].insert(0, brigade[1] if brigade[1] else "")
            self.brigade_entries["Контактная инфо"].delete(0, ctk.END)
            self.brigade_entries["Контактная инфо"].insert(0, brigade[2] if brigade[2] else "")

            self.editing_brigade_id = brigade_id
            self.save_brigade_button.configure(text="Обновить Бригаду", fg_color="#007BFF", hover_color="#0056B3")
            self.cancel_edit_brigade_button.configure(text="Отмена", fg_color="red", hover_color="darkred")
        else:
            messagebox.showwarning("Error", "Brigade not found.")
            logging.warning(f"Attempted to edit non-existent brigade ID:{brigade_id}")

    def delete_brigade(self, brigade_id):
        confirm = messagebox.askyesno("Confirm Deletion",
                                      f"Are you sure you want to delete brigade ID:{brigade_id}?")
        if confirm:
            success = self.db_manager.delete_brigade(brigade_id)
            if success:
                messagebox.showinfo("Success", f"Brigade ID:{brigade_id} successfully deleted.")
                self.apply_brigade_filters()
                if self.editing_brigade_id == brigade_id:
                    self.cancel_brigade_edit_mode()

    def cancel_brigade_edit_mode(self):
        self.editing_brigade_id = None
        self.clear_brigade_form()

    def apply_brigade_filters(self):
        search_query = self.brigade_search_entry.get().strip()
        self.load_brigades_to_display(search_query, self.current_sort_column_brigades, self.current_sort_order_brigades)

    def reset_brigade_filters(self):
        self.brigade_search_entry.delete(0, ctk.END)
        self.current_sort_column_brigades = "name"
        self.current_sort_order_brigades = "ASC"
        self.apply_brigade_filters()

    def sort_brigades(self, column_name):
        if self.current_sort_column_brigades == column_name:
            self.current_sort_order_brigades = "ASC" if self.current_sort_order_brigades == "DESC" else "DESC"
        else:
            self.current_sort_column_brigades = column_name
            self.current_sort_order_brigades = "ASC"
        self.apply_brigade_filters()

    def load_brigades_to_display(self, search_query="", sort_column="name", sort_order="ASC"):
        brigades = self.db_manager.get_brigades(search_query, sort_column, sort_order)

        for widget in self.brigade_display_widgets:
            widget.destroy()
        self.brigade_display_widgets.clear()

        for db_col, label in self.header_labels_brigades.items():
            display_text = ""
            for k, v in self.headers_info_brigades.items():
                if v == db_col:
                    display_text = k
                    break

            if db_col == sort_column:
                arrow = " ▲" if sort_order == "ASC" else " ▼"
                label.configure(text=f"{display_text}{arrow}")
            else:
                label.configure(text=display_text)

        current_row = 1
        row_colors = ("#343638", "#2b2b2b") if ctk.get_appearance_mode() == "Dark" else ("#ebebeb", "#e0e0e0")

        if not brigades:
            no_brigades_label = ctk.CTkLabel(self.brigades_list_scrollable_frame,
                                             text="No registered brigades.",
                                             font=ctk.CTkFont(size=14, slant="italic"))
            no_brigades_label.grid(row=current_row, column=0, columnspan=len(self.headers_info_brigades), padx=20,
                                   pady=20)
            self.brigade_display_widgets.append(no_brigades_label)
            return

        for brigade in brigades:
            brigade_id, name, specialization, contact_info = brigade
            bg_color = row_colors[current_row % 2]

            display_data = [str(brigade_id), name, specialization if specialization else "-",
                            contact_info if contact_info else "-"]

            for col_idx, data_item in enumerate(display_data):
                label = ctk.CTkLabel(self.brigades_list_scrollable_frame, text=data_item, wraplength=150,
                                     fg_color=bg_color, corner_radius=0)
                label.grid(row=current_row, column=col_idx, padx=1, pady=1, sticky="nsew")
                self.brigade_display_widgets.append(label)

            actions_frame = ctk.CTkFrame(self.brigades_list_scrollable_frame, fg_color="transparent")
            actions_frame.grid(row=current_row, column=len(display_data), padx=2, pady=1, sticky="ew")
            actions_frame.grid_columnconfigure((0, 1), weight=1)

            edit_button = ctk.CTkButton(actions_frame, text="Редактировать",
                                        command=lambda b_id=brigade_id: self.edit_brigade(b_id),
                                        corner_radius=6, width=90, fg_color="#36719F", hover_color="#4A80B3")
            edit_button.grid(row=0, column=0, padx=1, pady=1, sticky="ew")
            self.brigade_display_widgets.append(edit_button)

            delete_button = ctk.CTkButton(actions_frame, text="Удалить",
                                          command=lambda b_id=brigade_id: self.delete_brigade(b_id),
                                          corner_radius=6, width=90, fg_color="red", hover_color="darkred")
            delete_button.grid(row=0, column=1, padx=1, pady=1, sticky="ew")
            self.brigade_display_widgets.append(delete_button)
            self.brigade_display_widgets.append(actions_frame)

            current_row += 1

    def clear_equipment_form(self):
        for key, entry in self.equipment_entries.items():
            if isinstance(entry, ctk.CTkEntry):
                entry.delete(0, ctk.END)
        self.editing_equipment_id = None
        self.save_equipment_button.configure(text="Добавить Оборудование", fg_color="#00A86B", hover_color="#008C5A")
        self.cancel_edit_equipment_button.configure(text="Очистить/Отмена", fg_color="#6C757D", hover_color="#5A6268")

    def save_equipment_command(self):
        equipment_data = {key: entry.get() for key, entry in self.equipment_entries.items()}

        if not all([equipment_data["Название"], equipment_data["Тип"], equipment_data["Серийный номер"]]):
            messagebox.showwarning("Input Error", "Name, Type, and Serial Number are mandatory fields.")
            logging.warning("Attempted to save equipment with missing mandatory fields.")
            return

        for date_field in ["Дата установки (ГГГГ-ММ-ДД)", "Последнее обслуж. (ГГГГ-ММ-ДД)"]:
            if equipment_data[date_field]:
                try:
                    datetime.datetime.strptime(equipment_data[date_field], "%Y-%m-%d")
                except ValueError:
                    messagebox.showwarning("Invalid Date Format",
                                           f"Date in field '{date_field.replace('(ГГГГ-ММ-ДД):', '').strip()}' must be in YYYY-MM-DD format.")
                    logging.warning(f"Invalid date format for equipment field: {date_field}")
                    return

        success = self.db_manager.save_equipment(equipment_data, self.editing_equipment_id)
        if success:
            messagebox.showinfo("Success", f"Equipment successfully {'updated' if self.editing_equipment_id else 'added'}.")
            self.clear_equipment_form()
            self.apply_equipment_filters()

    def edit_equipment(self, equipment_id):
        equipment = self.db_manager.get_equipment_by_id(equipment_id)

        if equipment:
            labels = ["Название", "Тип", "Модель", "Серийный номер", "Дата установки (ГГГГ-ММ-ДД)", "Статус",
                      "Последнее обслуж. (ГГГГ-ММ-ДД)", "Местоположение"]
            for i, label_text in enumerate(labels):
                entry = self.equipment_entries[label_text]
                entry.delete(0, ctk.END)
                entry.insert(0, equipment[i] if equipment[i] else "")

            self.editing_equipment_id = equipment_id
            self.save_equipment_button.configure(text="Обновить Оборудование", fg_color="#007BFF", hover_color="#0056B3")
            self.cancel_edit_equipment_button.configure(text="Отмена", fg_color="red", hover_color="darkred")
        else:
            messagebox.showwarning("Error", "Equipment not found.")
            logging.warning(f"Attempted to edit non-existent equipment ID:{equipment_id}")

    def delete_equipment(self, equipment_id):
        confirm = messagebox.askyesno("Confirm Deletion",
                                      f"Are you sure you want to delete equipment ID:{equipment_id}?")
        if confirm:
            success = self.db_manager.delete_equipment(equipment_id)
            if success:
                messagebox.showinfo("Success", f"Equipment ID:{equipment_id} successfully deleted.")
                self.apply_equipment_filters()
                if self.editing_equipment_id == equipment_id:
                    self.cancel_equipment_edit_mode()

    def cancel_equipment_edit_mode(self):
        self.editing_equipment_id = None
        self.clear_equipment_form()

    def apply_equipment_filters(self):
        search_query = self.equipment_search_entry.get().strip()
        self.load_equipment_to_display(search_query, self.current_sort_column_equipment, self.current_sort_order_equipment)

    def reset_equipment_filters(self):
        self.equipment_search_entry.delete(0, ctk.END)
        self.current_sort_column_equipment = "name"
        self.current_sort_order_equipment = "ASC"
        self.apply_equipment_filters()

    def sort_equipment(self, column_name):
        if self.current_sort_column_equipment == column_name:
            self.current_sort_order_equipment = "ASC" if self.current_sort_order_equipment == "DESC" else "DESC"
        else:
            self.current_sort_column_equipment = column_name
            self.current_sort_order_equipment = "ASC"
        self.apply_equipment_filters()

    def load_equipment_to_display(self, search_query="", sort_column="name", sort_order="ASC"):
        equipment_list = self.db_manager.get_equipment(search_query, sort_column, sort_order)

        for widget in self.equipment_display_widgets:
            widget.destroy()
        self.equipment_display_widgets.clear()

        for db_col, label in self.header_labels_equipment.items():
            display_text = ""
            for k, v in self.headers_info_equipment.items():
                if v == db_col:
                    display_text = k
                    break

            if db_col == sort_column:
                arrow = " ▲" if sort_order == "ASC" else " ▼"
                label.configure(text=f"{display_text}{arrow}")
            else:
                label.configure(text=display_text)

        current_row = 1
        row_colors = ("#343638", "#2b2b2b") if ctk.get_appearance_mode() == "Dark" else ("#ebebeb", "#e0e0e0")

        if not equipment_list:
            no_equipment_label = ctk.CTkLabel(self.equipment_list_scrollable_frame,
                                              text="No registered equipment.",
                                              font=ctk.CTkFont(size=14, slant="italic"))
            no_equipment_label.grid(row=current_row, column=0, columnspan=len(self.headers_info_equipment), padx=20,
                                    pady=20)
            self.equipment_display_widgets.append(no_equipment_label)
            return

        for item in equipment_list:
            (equipment_id, name, eq_type, model, serial_number, installation_date,
             status, last_maintenance_date, location) = item
            bg_color = row_colors[current_row % 2]

            display_data = [
                str(equipment_id),
                name,
                eq_type,
                model if model else "-",
                serial_number,
                installation_date if installation_date else "-",
                status if status else "-",
                last_maintenance_date if last_maintenance_date else "-",
                location if location else "-"
            ]

            for col_idx, data_item in enumerate(display_data):
                label = ctk.CTkLabel(self.equipment_list_scrollable_frame, text=data_item, wraplength=100,
                                     fg_color=bg_color, corner_radius=0)
                label.grid(row=current_row, column=col_idx, padx=1, pady=1, sticky="nsew")
                self.equipment_display_widgets.append(label)

            actions_frame = ctk.CTkFrame(self.equipment_list_scrollable_frame, fg_color="transparent")
            actions_frame.grid(row=current_row, column=len(display_data), padx=2, pady=1, sticky="ew")
            actions_frame.grid_columnconfigure((0, 1), weight=1)

            edit_button = ctk.CTkButton(actions_frame, text="Редактировать",
                                        command=lambda e_id=equipment_id: self.edit_equipment(e_id),
                                        corner_radius=6, width=90, fg_color="#36719F", hover_color="#4A80B3")
            edit_button.grid(row=0, column=0, padx=1, pady=1, sticky="ew")
            self.equipment_display_widgets.append(edit_button)

            delete_button = ctk.CTkButton(actions_frame, text="Удалить",
                                          command=lambda e_id=equipment_id: self.delete_equipment(e_id),
                                          corner_radius=6, width=90, fg_color="red", hover_color="darkred")
            delete_button.grid(row=0, column=1, padx=1, pady=1, sticky="ew")
            self.equipment_display_widgets.append(delete_button)
            self.equipment_display_widgets.append(actions_frame)

            current_row += 1


if __name__ == "__main__":
    app = App()
    app.mainloop()
