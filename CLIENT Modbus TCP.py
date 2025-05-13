from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread
import time

class ModbusClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modbus TCP Клиент")
        self.root.geometry("900x700")
        
        # Главный контейнер с прокруткой
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.main_frame)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Настройка прокрутки
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Привязываем колесо мыши к прокрутке
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Переменные для подключения
        self.client = None
        self.connected = False
        self.polling_active = False
        self.unit_id = 1
        
        # Создаем GUI
        self.create_widgets()
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def create_widgets(self):
        """Создание интерфейса клиента"""
        # Основные параметры подключения
        connection_frame = ttk.LabelFrame(self.scrollable_frame, text="Настройки подключения")
        connection_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Используем grid внутри frame
        ttk.Label(connection_frame, text="IP адрес сервера:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.ip_entry = ttk.Entry(connection_frame)
        self.ip_entry.grid(row=0, column=1, padx=5)
        self.ip_entry.insert(0, "127.0.0.1")
        
        ttk.Label(connection_frame, text="Порт:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.port_entry = ttk.Entry(connection_frame)
        self.port_entry.grid(row=1, column=1, padx=5)
        self.port_entry.insert(0, "5020")
        
        ttk.Label(connection_frame, text="ID устройства:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.unit_entry = ttk.Entry(connection_frame)
        self.unit_entry.grid(row=2, column=1, padx=5)
        self.unit_entry.insert(0, "1")
        
        # Кнопки подключения
        self.connect_button = ttk.Button(connection_frame, text="Подключиться", command=self.connect)
        self.connect_button.grid(row=3, column=0, pady=10, padx=5)
        
        self.disconnect_button = ttk.Button(connection_frame, text="Отключиться", command=self.disconnect, state=tk.DISABLED)
        self.disconnect_button.grid(row=3, column=1, pady=10, padx=5)
        
        # Статус подключения
        self.status_label = ttk.Label(connection_frame, text="Отключен", foreground="red")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=5)
        
        # Вкладки для разных функций Modbus
        self.create_tabs()
        
        # Панель датчика PT-100
        self.create_sensor_panel()
        
        # Индикатор дискретного сигнала
        self.create_lamp_indicator()
    
    def create_tabs(self):
        """Создание вкладок с использованием pack()"""
        tab_control = ttk.Notebook(self.scrollable_frame)
        tab_control.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Создаем вкладки
        self.tab_coils = ttk.Frame(tab_control)
        self.tab_discrete_inputs = ttk.Frame(tab_control)
        self.tab_holding_registers = ttk.Frame(tab_control)
        self.tab_input_registers = ttk.Frame(tab_control)
        self.tab_write = ttk.Frame(tab_control)
        
        tab_control.add(self.tab_coils, text="Coils")
        tab_control.add(self.tab_discrete_inputs, text="Discrete Inputs")
        tab_control.add(self.tab_holding_registers, text="Holding Registers")
        tab_control.add(self.tab_input_registers, text="Input Registers")
        tab_control.add(self.tab_write, text="Запись")
        
        # Заполняем вкладки
        self.fill_coils_tab()
        self.fill_discrete_inputs_tab()
        self.fill_holding_registers_tab()
        self.fill_input_registers_tab()
        self.fill_write_tab()
    
    def fill_coils_tab(self):
        """Заполнение вкладки Coils"""
        ttk.Label(self.tab_coils, text="Чтение Coils (дискретных выходов)").pack(pady=5)
        
        frame = ttk.Frame(self.tab_coils)
        frame.pack(pady=5)
        
        ttk.Label(frame, text="Начальный адрес:").grid(row=0, column=0, padx=5)
        self.coils_start_addr = ttk.Entry(frame, width=10)
        self.coils_start_addr.grid(row=0, column=1, padx=5)
        self.coils_start_addr.insert(0, "0")
        
        ttk.Label(frame, text="Количество:").grid(row=0, column=2, padx=5)
        self.coils_count = ttk.Entry(frame, width=10)
        self.coils_count.grid(row=0, column=3, padx=5)
        self.coils_count.insert(0, "5")
        
        ttk.Button(self.tab_coils, text="Прочитать", command=self.read_coils).pack(pady=5)
        self.coils_result_label = ttk.Label(self.tab_coils, text="")
        self.coils_result_label.pack(pady=5)
        
        self.coils_poll_var = tk.IntVar()
        ttk.Checkbutton(self.tab_coils, text="Автоматический опрос", 
                       variable=self.coils_poll_var,
                       command=self.toggle_coils_polling).pack(pady=5)
        
        interval_frame = ttk.Frame(self.tab_coils)
        interval_frame.pack()
        
        ttk.Label(interval_frame, text="Интервал (мс):").pack(side=tk.LEFT)
        self.coils_poll_interval = ttk.Entry(interval_frame, width=10)
        self.coils_poll_interval.pack(side=tk.LEFT, padx=5)
        self.coils_poll_interval.insert(0, "1000")
    
    def fill_discrete_inputs_tab(self):
        """Заполнение вкладки Discrete Inputs"""
        ttk.Label(self.tab_discrete_inputs, text="Чтение Discrete Inputs (дискретных входов)").pack(pady=5)
        
        frame = ttk.Frame(self.tab_discrete_inputs)
        frame.pack(pady=5)
        
        ttk.Label(frame, text="Начальный адрес:").grid(row=0, column=0, padx=5)
        self.discrete_inputs_start_addr = ttk.Entry(frame, width=10)
        self.discrete_inputs_start_addr.grid(row=0, column=1, padx=5)
        self.discrete_inputs_start_addr.insert(0, "0")
        
        ttk.Label(frame, text="Количество:").grid(row=0, column=2, padx=5)
        self.discrete_inputs_count = ttk.Entry(frame, width=10)
        self.discrete_inputs_count.grid(row=0, column=3, padx=5)
        self.discrete_inputs_count.insert(0, "5")
        
        ttk.Button(self.tab_discrete_inputs, text="Прочитать", command=self.read_discrete_inputs).pack(pady=5)
        self.discrete_inputs_result_label = ttk.Label(self.tab_discrete_inputs, text="")
        self.discrete_inputs_result_label.pack(pady=5)
        
        self.discrete_inputs_poll_var = tk.IntVar()
        ttk.Checkbutton(self.tab_discrete_inputs, text="Автоматический опрос", 
                       variable=self.discrete_inputs_poll_var,
                       command=self.toggle_discrete_inputs_polling).pack(pady=5)
        
        interval_frame = ttk.Frame(self.tab_discrete_inputs)
        interval_frame.pack()
        
        ttk.Label(interval_frame, text="Интервал (мс):").pack(side=tk.LEFT)
        self.discrete_inputs_poll_interval = ttk.Entry(interval_frame, width=10)
        self.discrete_inputs_poll_interval.pack(side=tk.LEFT, padx=5)
        self.discrete_inputs_poll_interval.insert(0, "1000")
    
    def fill_holding_registers_tab(self):
        """Заполнение вкладки Holding Registers"""
        ttk.Label(self.tab_holding_registers, text="Чтение Holding Registers (регистров хранения)").pack(pady=5)
        
        frame = ttk.Frame(self.tab_holding_registers)
        frame.pack(pady=5)
        
        ttk.Label(frame, text="Начальный адрес:").grid(row=0, column=0, padx=5)
        self.holding_registers_start_addr = ttk.Entry(frame, width=10)
        self.holding_registers_start_addr.grid(row=0, column=1, padx=5)
        self.holding_registers_start_addr.insert(0, "0")
        
        ttk.Label(frame, text="Количество:").grid(row=0, column=2, padx=5)
        self.holding_registers_count = ttk.Entry(frame, width=10)
        self.holding_registers_count.grid(row=0, column=3, padx=5)
        self.holding_registers_count.insert(0, "5")
        
        ttk.Button(self.tab_holding_registers, text="Прочитать", command=self.read_holding_registers).pack(pady=5)
        self.holding_registers_result_label = ttk.Label(self.tab_holding_registers, text="")
        self.holding_registers_result_label.pack(pady=5)
        
        self.holding_registers_poll_var = tk.IntVar()
        ttk.Checkbutton(self.tab_holding_registers, text="Автоматический опрос", 
                       variable=self.holding_registers_poll_var,
                       command=self.toggle_holding_registers_polling).pack(pady=5)
        
        interval_frame = ttk.Frame(self.tab_holding_registers)
        interval_frame.pack()
        
        ttk.Label(interval_frame, text="Интервал (мс):").pack(side=tk.LEFT)
        self.holding_registers_poll_interval = ttk.Entry(interval_frame, width=10)
        self.holding_registers_poll_interval.pack(side=tk.LEFT, padx=5)
        self.holding_registers_poll_interval.insert(0, "1000")
    
    def fill_input_registers_tab(self):
        """Заполнение вкладки Input Registers"""
        ttk.Label(self.tab_input_registers, text="Чтение Input Registers (входных регистров)").pack(pady=5)
        
        frame = ttk.Frame(self.tab_input_registers)
        frame.pack(pady=5)
        
        ttk.Label(frame, text="Начальный адрес:").grid(row=0, column=0, padx=5)
        self.input_registers_start_addr = ttk.Entry(frame, width=10)
        self.input_registers_start_addr.grid(row=0, column=1, padx=5)
        self.input_registers_start_addr.insert(0, "0")
        
        ttk.Label(frame, text="Количество:").grid(row=0, column=2, padx=5)
        self.input_registers_count = ttk.Entry(frame, width=10)
        self.input_registers_count.grid(row=0, column=3, padx=5)
        self.input_registers_count.insert(0, "5")
        
        ttk.Button(self.tab_input_registers, text="Прочитать", command=self.read_input_registers).pack(pady=5)
        self.input_registers_result_label = ttk.Label(self.tab_input_registers, text="")
        self.input_registers_result_label.pack(pady=5)
        
        self.input_registers_poll_var = tk.IntVar()
        ttk.Checkbutton(self.tab_input_registers, text="Автоматический опрос", 
                       variable=self.input_registers_poll_var,
                       command=self.toggle_input_registers_polling).pack(pady=5)
        
        interval_frame = ttk.Frame(self.tab_input_registers)
        interval_frame.pack()
        
        ttk.Label(interval_frame, text="Интервал (мс):").pack(side=tk.LEFT)
        self.input_registers_poll_interval = ttk.Entry(interval_frame, width=10)
        self.input_registers_poll_interval.pack(side=tk.LEFT, padx=5)
        self.input_registers_poll_interval.insert(0, "1000")
    
    def fill_write_tab(self):
        """Заполнение вкладки записи"""
        ttk.Label(self.tab_write, text="Запись значений").pack(pady=5)
        
        frame_type = ttk.Frame(self.tab_write)
        frame_type.pack(pady=5)
        
        ttk.Label(frame_type, text="Тип:").grid(row=0, column=0, padx=5)
        self.write_type = ttk.Combobox(frame_type, values=["Coil", "Holding Register"], state="readonly")
        self.write_type.grid(row=0, column=1, padx=5)
        self.write_type.current(0)
        
        frame_params = ttk.Frame(self.tab_write)
        frame_params.pack(pady=5)
        
        ttk.Label(frame_params,text="Адрес:").grid(row=0, column=0, padx=5)
        self.write_address = ttk.Entry(frame_params, width=10)
        self.write_address.grid(row=0, column=1, padx=5)
        self.write_address.insert(0, "0")
        
        ttk.Label(frame_params, text="Значение:").grid(row=0, column=2, padx=5)
        self.write_value = ttk.Entry(frame_params, width=10)
        self.write_value.grid(row=0, column=3, padx=5)
        self.write_value.insert(0, "1")
        
        ttk.Button(self.tab_write, text="Записать", command=self.write_value_command).pack(pady=5)
        self.write_result_label = ttk.Label(self.tab_write, text="")
        self.write_result_label.pack(pady=5)
    
    def create_sensor_panel(self):
        """Создание панели для датчика PT-100"""
        self.sensor_frame = ttk.LabelFrame(self.scrollable_frame, 
                                         text="Датчик давления PT-100",
                                         padding=(10, 5))
        self.sensor_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # График значений
        self.graph_canvas = tk.Canvas(self.sensor_frame, width=800, height=300, bg="white")
        self.graph_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Параметры чтения
        control_frame = ttk.Frame(self.sensor_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(control_frame, text="Начальный адрес:").pack(side=tk.LEFT, padx=5)
        self.sensor_start_addr = ttk.Entry(control_frame, width=10)
        self.sensor_start_addr.pack(side=tk.LEFT, padx=5)
        self.sensor_start_addr.insert(0, "0")
        
        ttk.Label(control_frame, text="Количество:").pack(side=tk.LEFT, padx=5)
        self.sensor_count = ttk.Entry(control_frame, width=10)
        self.sensor_count.pack(side=tk.LEFT, padx=5)
        self.sensor_count.insert(0, "5")
        
        # Кнопки управления
        btn_frame = ttk.Frame(self.sensor_frame)
        btn_frame.pack(pady=5)
        
        ttk.Button(btn_frame, text="Прочитать датчик", command=self.read_sensor_values).pack(side=tk.LEFT, padx=5)
        
        # Текущее значение
        self.sensor_value_label = ttk.Label(self.sensor_frame, text="Текущее значение: -", font=('Arial', 12))
        self.sensor_value_label.pack(pady=5)
        
        # Автоматическое обновление
        self.sensor_poll_var = tk.IntVar()
        ttk.Checkbutton(self.sensor_frame, text="Автообновление", 
                       variable=self.sensor_poll_var,
                       command=self.toggle_sensor_polling).pack(pady=5)
        
        interval_frame = ttk.Frame(self.sensor_frame)
        interval_frame.pack()
        
        ttk.Label(interval_frame, text="Интервал (мс):").pack(side=tk.LEFT)
        self.sensor_poll_interval = ttk.Entry(interval_frame, width=10)
        self.sensor_poll_interval.pack(side=tk.LEFT, padx=5)
        self.sensor_poll_interval.insert(0, "1000")
        
        # История значений для графика
        self.sensor_history = []
        self.max_history = 20
    
    def create_lamp_indicator(self):
        """Создание индикатора лампочки для дискретного сигнала"""
        self.lamp_frame = ttk.LabelFrame(self.scrollable_frame, text="Индикатор дискретного сигнала")
        self.lamp_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Холст для лампочки
        self.lamp_canvas = tk.Canvas(self.lamp_frame, width=60, height=60, bg="white")
        self.lamp_canvas.pack(pady=5)
        
        # Создаем лампочку (выключенное состояние)
        self.lamp = self.lamp_canvas.create_oval(10, 10, 50, 50, fill="gray", outline="black")
        
        # Надпись состояния
        self.lamp_state_label = ttk.Label(self.lamp_frame, text="Состояние: неизвестно")
        self.lamp_state_label.pack()
        
        # Выбор типа сигнала и адреса
        frame_type = ttk.Frame(self.lamp_frame)
        frame_type.pack(pady=5)
        
        ttk.Label(frame_type, text="Тип сигнала:").pack(side=tk.LEFT)
        self.lamp_signal_type = ttk.Combobox(frame_type, values=["Coil", "Discrete Input"], state="readonly")
        self.lamp_signal_type.pack(side=tk.LEFT, padx=5)
        self.lamp_signal_type.current(0)
        
        ttk.Label(frame_type, text="Адрес:").pack(side=tk.LEFT)
        self.lamp_signal_addr = ttk.Spinbox(frame_type, from_=0, to=99, width=5)
        self.lamp_signal_addr.pack(side=tk.LEFT, padx=5)
        self.lamp_signal_addr.set(0)
        
        # Кнопки управления
        btn_frame = ttk.Frame(self.lamp_frame)
        btn_frame.pack(pady=5)
        
        ttk.Button(btn_frame, text="Проверить", command=self.check_lamp_state).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Включить", command=lambda: self.set_lamp_state(1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Выключить", command=lambda: self.set_lamp_state(0)).pack(side=tk.LEFT, padx=5)
        
        # Настройки автоматического обновления
        self.lamp_poll_var = tk.IntVar()
        ttk.Checkbutton(self.lamp_frame, text="Автообновление", 
                       variable=self.lamp_poll_var,
                       command=self.toggle_lamp_polling).pack(pady=5)
        
        poll_frame = ttk.Frame(self.lamp_frame)
        poll_frame.pack()
        
        ttk.Label(poll_frame, text="Интервал (мс):").pack(side=tk.LEFT)
        self.lamp_poll_interval = ttk.Entry(poll_frame, width=6)
        self.lamp_poll_interval.pack(side=tk.LEFT, padx=5)
        self.lamp_poll_interval.insert(0, "1000")
    
    def update_sensor_graph(self, value):
        """Обновление графика с новым значением датчика"""
        # Добавляем новое значение в историю
        self.sensor_history.append(value)
        if len(self.sensor_history) > self.max_history:
            self.sensor_history.pop(0)
        
        # Очищаем холст
        self.graph_canvas.delete("all")
        
        # Получаем текущие размеры холста
        canvas_width = self.graph_canvas.winfo_width()
        canvas_height = self.graph_canvas.winfo_height()
        
        # Рассчитываем отступы и масштаб
        padding = 50
        graph_width = canvas_width - 2 * padding
        graph_height = canvas_height - 2 * padding
        scale_y = graph_height / 20  # Для диапазона 0-20
        
        # Рисуем оси
        self.graph_canvas.create_line(padding, padding, padding, padding + graph_height, width=2)  # Y ось
        self.graph_canvas.create_line(padding, padding + graph_height, padding + graph_width, padding + graph_height, width=2)  # X ось
        
        # Подписи осей
        self.graph_canvas.create_text(padding + graph_width/2, padding + graph_height + 20, 
                                    text="Время", font=('Arial', 10))
        self.graph_canvas.create_text(padding - 20, padding + graph_height/2, 
                                    text="Давление", angle=90, font=('Arial', 10))
        
        # Шкала значений (0-20)
        for i in range(0, 21, 5):
            y = padding + graph_height - (i * scale_y)
            self.graph_canvas.create_line(padding - 5, y, padding, y, width=2)
            self.graph_canvas.create_text(padding - 10, y, text=str(i), anchor="e", font=('Arial', 8))
        
        # Рисуем график
        if len(self.sensor_history) > 1:
            for i in range(1, len(self.sensor_history)):
                x1 = padding + (i-1) * (graph_width / (self.max_history-1))
                y1 = padding + graph_height - (self.sensor_history[i-1] * scale_y)
                x2 = padding + i * (graph_width / (self.max_history-1))
                y2 = padding + graph_height - (self.sensor_history[i] * scale_y)
                self.graph_canvas.create_line(x1, y1, x2, y2, fill="blue", width=2)
        
        # Точки на графике
        for i, val in enumerate(self.sensor_history):
            x = padding + i * (graph_width / (self.max_history-1))
            y = padding + graph_height - (val * scale_y)
            self.graph_canvas.create_oval(x-3, y-3, x+3, y+3, fill="red")
        
        # Обновляем текстовое значение
        self.sensor_value_label.config(text=f"Текущее значение: {value}")
    
    def read_sensor_values(self):
        """Чтение значений датчика PT-100 (Holding Registers)"""
        if not self.connected:
            messagebox.showerror("Ошибка", "Не подключено к серверу")
            return
        
        try:
            start_addr = int(self.sensor_start_addr.get())
            count = int(self.sensor_count.get())
            
            result = self.client.read_holding_registers(address=start_addr, count=count, slave=self.unit_id)
            
            if result.isError():
                messagebox.showerror("Ошибка", f"Ошибка чтения: {result}")
            else:
                values = result.registers
                if values:
                    self.update_sensor_graph(values[0])
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный адрес или количество")
        except ModbusException as e:
            messagebox.showerror("Ошибка Modbus", str(e))
    
    def toggle_sensor_polling(self):
        """Включение/выключение автоматического опроса датчика"""
        if self.sensor_poll_var.get():
            self.start_sensor_polling()
        else:
            self.stop_sensor_polling()
    
    def start_sensor_polling(self):
        """Запуск автоматического опроса датчика"""
        if not self.polling_active:
            self.polling_active = True
            Thread(target=self.sensor_polling_loop, daemon=True).start()
    
    def stop_sensor_polling(self):
        """Остановка автоматического опроса датчика"""
        self.polling_active = False
    
    def sensor_polling_loop(self):
        """Цикл автоматического опроса датчика"""
        while self.polling_active and self.sensor_poll_var.get() and self.connected:
            try:
                interval = int(self.sensor_poll_interval.get())
                self.read_sensor_values()
                time.sleep(interval / 1000)
            except:
                time.sleep(1)
    
    def connect(self):
        """Подключение к серверу Modbus"""
        if not self.connected:
            ip = self.ip_entry.get()
            port = int(self.port_entry.get())
            self.unit_id = int(self.unit_entry.get())
            
            try:
                self.client = ModbusTcpClient(ip, port=port)
                self.client.connect()
                
                self.connected = True
                self.connect_button.config(state=tk.DISABLED)
                self.disconnect_button.config(state=tk.NORMAL)
                self.status_label.config(text="Подключен", foreground="green")
                
                messagebox.showinfo("Подключение", "Успешно подключено к серверу Modbus")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось подключиться: {str(e)}")
    
    def disconnect(self):
        """Отключение от сервера Modbus"""
        if self.connected:
            try:
                self.client.close()
                self.connected = False
                self.connect_button.config(state=tk.NORMAL)
                self.disconnect_button.config(state=tk.DISABLED)
                self.status_label.config(text="Отключен", foreground="red")
                
                # Останавливаем все опросы
                self.polling_active = False
                
                messagebox.showinfo("Отключение", "Соединение с сервером Modbus закрыто")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось отключиться: {str(e)}")
    
    def read_coils(self):
        """Чтение Coils"""
        if not self.connected:
            messagebox.showerror("Ошибка", "Не подключено к серверу")
            return
        
        try:
            start_addr = int(self.coils_start_addr.get())
            count = int(self.coils_count.get())
            
            result = self.client.read_coils(address=start_addr, count=count, slave=self.unit_id)
            
            if result.isError():
                self.coils_result_label.config(text=f"Ошибка: {result}")
            else:
                values = result.bits[:count]
                self.coils_result_label.config(text=f"Значения: {values}")
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный адрес или количество")
        except ModbusException as e:
            messagebox.showerror("Ошибка Modbus", str(e))
    
    def read_discrete_inputs(self):
        """Чтение Discrete Inputs"""
        if not self.connected:
            messagebox.showerror("Ошибка", "Не подключено к серверу")
            return
        
        try:
            start_addr = int(self.discrete_inputs_start_addr.get())
            count = int(self.discrete_inputs_count.get())
            
            result = self.client.read_discrete_inputs(address=start_addr, count=count, slave=self.unit_id)
            
            if result.isError():
                self.discrete_inputs_result_label.config(text=f"Ошибка: {result}")
            else:
                values = result.bits[:count]
                self.discrete_inputs_result_label.config(text=f"Значения: {values}")
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный адрес или количество")
        except ModbusException as e:
            messagebox.showerror("Ошибка Modbus", str(e))
    
    def read_holding_registers(self):
        """Чтение Holding Registers"""
        if not self.connected:
            messagebox.showerror("Ошибка", "Не подключено к серверу")
            return
        
        try:
            start_addr = int(self.holding_registers_start_addr.get())
            count = int(self.holding_registers_count.get())
            
            result = self.client.read_holding_registers(address=start_addr, count=count, slave=self.unit_id)
            
            if result.isError():
                self.holding_registers_result_label.config(text=f"Ошибка: {result}")
            else:
                values = result.registers
                self.holding_registers_result_label.config(text=f"Значения: {values}")
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный адрес или количество")
        except ModbusException as e:
            messagebox.showerror("Ошибка Modbus", str(e))
    
    def read_input_registers(self):
        """Чтение Input Registers"""
        if not self.connected:
            messagebox.showerror("Ошибка", "Не подключено к серверу")
            return
        
        try:
            start_addr = int(self.input_registers_start_addr.get())
            count = int(self.input_registers_count.get())
            
            result = self.client.read_input_registers(address=start_addr, count=count, slave=self.unit_id)
            
            if result.isError():
                self.input_registers_result_label.config(text=f"Ошибка: {result}")
            else:
                values = result.registers
                self.input_registers_result_label.config(text=f"Значения: {values}")
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный адрес или количество")
        except ModbusException as e:
            messagebox.showerror("Ошибка Modbus", str(e))
    
    def write_value_command(self):
        """Запись значения"""
        if not self.connected:
            messagebox.showerror("Ошибка", "Не подключено к серверу")
            return
        
        try:
            write_type = self.write_type.get()
            address = int(self.write_address.get())
            value = self.write_value.get()
            
            if write_type == "Coil":
                value = int(value)
                if value not in (0, 1):
                    raise ValueError("Для Coil значение должно быть 0 или 1")
                
                result = self.client.write_coil(address=address, value=value, slave=self.unit_id)
            elif write_type == "Holding Register":
                value = int(value)
                if value < 0 or value > 65535:
                    raise ValueError("Для Holding Register значение должно быть от 0 до 65535")
                
                result = self.client.write_register(address=address, value=value, slave=self.unit_id)
            else:
                raise ValueError("Неизвестный тип записи")
            
            if result.isError():
                self.write_result_label.config(text=f"Ошибка: {result}")
            else:
                self.write_result_label.config(text="Запись успешна")
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))
        except ModbusException as e:
            messagebox.showerror("Ошибка Modbus", str(e))
    
    def check_lamp_state(self):
        """Проверка состояния лампочки (Coil или Discrete Input)"""
        if not self.connected:
            messagebox.showerror("Ошибка", "Не подключено к серверу")
            return
        
        try:
            signal_type = self.lamp_signal_type.get()
            address = int(self.lamp_signal_addr.get())
            
            if signal_type == "Coil":
                result = self.client.read_coils(address=address, count=1, slave=self.unit_id)
            elif signal_type == "Discrete Input":
                result = self.client.read_discrete_inputs(address=address, count=1, slave=self.unit_id)
            else:
                messagebox.showerror("Ошибка", "Неизвестный тип сигнала")
                return
            
            if result.isError():
                messagebox.showerror("Ошибка", f"Ошибка чтения: {result}")
            else:
                state = result.bits[0]
                self.update_lamp_indicator(state, signal_type, address)
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный адрес")
        except ModbusException as e:
            messagebox.showerror("Ошибка Modbus", str(e))
    
    def update_lamp_indicator(self, state, signal_type=None, address=None):
        """Обновление индикатора лампочки"""
        if signal_type is None:
            signal_type = self.lamp_signal_type.get()
        if address is None:
            address = int(self.lamp_signal_addr.get())
            
        color = "yellow" if state else "gray"
        self.lamp_canvas.itemconfig(self.lamp, fill=color)
        status = "ВКЛ" if state else "ВЫКЛ"
        self.lamp_state_label.config(text=f"Состояние: {status} ({signal_type} {address})")

    def set_lamp_state(self, state):
        """Установка состояния лампочки (только для Coils)"""
        if not self.connected:
            messagebox.showerror("Ошибка", "Не подключено к серверу")
            return
        
        signal_type = self.lamp_signal_type.get()
        if signal_type != "Coil":
            messagebox.showerror("Ошибка", "Запись возможна только для Coils")
            return
        
        try:
            address = int(self.lamp_signal_addr.get())
            result = self.client.write_coil(address=address, value=state, slave=self.unit_id)
            
            if result.isError():
                messagebox.showerror("Ошибка", f"Ошибка записи: {result}")
            else:
                self.update_lamp_indicator(state, signal_type, address)
                messagebox.showinfo("Успех", f"Coil {address} установлен в {state}")
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный адрес Coil")
        except ModbusException as e:
            messagebox.showerror("Ошибка Modbus", str(e))

    def toggle_lamp_polling(self):
        """Включение/выключение автоматического опроса состояния лампочки"""
        if self.lamp_poll_var.get():
            self.start_lamp_polling()
        else:
            self.stop_lamp_polling()

    def start_lamp_polling(self):
        """Запуск автоматического опроса состояния лампочки"""
        if not hasattr(self, '_lamp_polling_active'):
            self._lamp_polling_active = True
            self._lamp_polling_loop()

    def stop_lamp_polling(self):
        """Остановка автоматического опроса состояния лампочки"""
        if hasattr(self, '_lamp_polling_active'):
            self._lamp_polling_active = False

    def _lamp_polling_loop(self):
        """Цикл автоматического опроса состояния лампочки"""
        if getattr(self, '_lamp_polling_active', False) and self.lamp_poll_var.get() and self.connected:
            try:
                interval = int(self.lamp_poll_interval.get())
                self.check_lamp_state()
                self.root.after(interval, self._lamp_polling_loop)
            except ValueError:
                self.root.after(1000, self._lamp_polling_loop)
    
    def toggle_coils_polling(self):
        """Включение/выключение автоматического опроса Coils"""
        if self.coils_poll_var.get():
            self.start_coils_polling()
        else:
            self.stop_coils_polling()
    
    def start_coils_polling(self):
        """Запуск автоматического опроса Coils"""
        if not self.polling_active:
            self.polling_active = True
            Thread(target=self.coils_polling_loop, daemon=True).start()
    
    def stop_coils_polling(self):
        """Остановка автоматического опроса Coils"""
        self.polling_active = False
    
    def coils_polling_loop(self):
        """Цикл автоматического опроса Coils"""
        while self.polling_active and self.coils_poll_var.get() and self.connected:
            try:
                interval = int(self.coils_poll_interval.get())
                start_addr = int(self.coils_start_addr.get())
                count = int(self.coils_count.get())
                
                result = self.client.read_coils(start_addr, count, slave=self.unit_id)
                
                if not result.isError():
                    values = result.bits[:count]
                    self.coils_result_label.config(text=f"Значения: {values}")
                
                time.sleep(interval / 1000)
            except:
                time.sleep(1)
    
    def toggle_discrete_inputs_polling(self):
        """Включение/выключение автоматического опроса Discrete Inputs"""
        if self.discrete_inputs_poll_var.get():
            self.start_discrete_inputs_polling()
        else:
            self.stop_discrete_inputs_polling()
    
    def start_discrete_inputs_polling(self):
        """Запуск автоматического опроса Discrete Inputs"""
        if not self.polling_active:
            self.polling_active = True
            Thread(target=self.discrete_inputs_polling_loop, daemon=True).start()
    
    def stop_discrete_inputs_polling(self):
        """Остановка автоматического опроса Discrete Inputs"""
        self.polling_active = False
    
    def discrete_inputs_polling_loop(self):
        """Цикл автоматического опроса Discrete Inputs"""
        while self.polling_active and self.discrete_inputs_poll_var.get() and self.connected:
            try:
                interval = int(self.discrete_inputs_poll_interval.get())
                start_addr = int(self.discrete_inputs_start_addr.get())
                count = int(self.discrete_inputs_count.get())
                
                result = self.client.read_discrete_inputs(start_addr, count, slave=self.unit_id)
                
                if not result.isError():
                    values = result.bits[:count]
                    self.discrete_inputs_result_label.config(text=f"Значения: {values}")
                
                time.sleep(interval / 1000)
            except:
                time.sleep(1)
    
    def toggle_holding_registers_polling(self):
        """Включение/выключение автоматического опроса Holding Registers"""
        if self.holding_registers_poll_var.get():
            self.start_holding_registers_polling()
        else:
            self.stop_holding_registers_polling()
    
    def start_holding_registers_polling(self):
        """Запуск автоматического опроса Holding Registers"""
        if not self.polling_active:
            self.polling_active = True
            Thread(target=self.holding_registers_polling_loop, daemon=True).start()
    
    def stop_holding_registers_polling(self):
        """Остановка автоматического опроса Holding Registers"""
        self.polling_active = False
    
    def holding_registers_polling_loop(self):
        """Цикл автоматического опроса Holding Registers"""
        while self.polling_active and self.holding_registers_poll_var.get() and self.connected:
            try:
                interval = int(self.holding_registers_poll_interval.get())
                start_addr = int(self.holding_registers_start_addr.get())
                count = int(self.holding_registers_count.get())
                
                result = self.client.read_holding_registers(start_addr, count, slave=self.unit_id)
                
                if not result.isError():
                    values = result.registers
                    self.holding_registers_result_label.config(text=f"Значения: {values}")
                
                time.sleep(interval / 1000)
            except:
                time.sleep(1)
    
    def toggle_input_registers_polling(self):
        """Включение/выключение автоматического опроса Input Registers"""
        if self.input_registers_poll_var.get():
            self.start_input_registers_polling()
        else:
            self.stop_input_registers_polling()
    
    def start_input_registers_polling(self):
        """Запуск автоматического опроса Input Registers"""
        if not self.polling_active:
            self.polling_active = True
            Thread(target=self.input_registers_polling_loop, daemon=True).start()
    
    def stop_input_registers_polling(self):
        """Остановка автоматического опроса Input Registers"""
        self.polling_active = False
    
    def input_registers_polling_loop(self):
        """Цикл автоматического опроса Input Registers"""
        while self.polling_active and self.input_registers_poll_var.get() and self.connected:
            try:
                interval = int(self.input_registers_poll_interval.get())
                start_addr = int(self.input_registers_start_addr.get())
                count = int(self.input_registers_count.get())
                
                result = self.client.read_input_registers(start_addr, count, slave=self.unit_id)
                
                if not result.isError():
                    values = result.registers
                    self.input_registers_result_label.config(text=f"Значения: {values}")
                
                time.sleep(interval / 1000)
            except:
                time.sleep(1)

    def toggle_lamp_polling(self):
        """Включение/выключение автоматического опроса состояния лампочки"""
        if self.lamp_poll_var.get():
            self.start_lamp_polling()
        else:
            self.stop_lamp_polling()
    
    def start_lamp_polling(self):
        """Запуск автоматического опроса состояния лампочки"""
        if not self.polling_active:
            self.polling_active = True
            Thread(target=self.lamp_polling_loop, daemon=True).start()
    
    def stop_lamp_polling(self):
        """Остановка автоматического опроса состояния лампочки"""
        self.polling_active = False
    
    def lamp_polling_loop(self):
        """Цикл автоматического опроса состояния лампочки"""
        while self.polling_active and self.lamp_poll_var.get() and self.connected:
            try:
                interval = int(self.lamp_poll_interval.get())
                
                result = self.client.read_coils(0, 1)
                
                if not result.isError():
                    state = result.bits[0]
                    self.update_lamp_indicator(state)
                
                time.sleep(interval / 1000)
            except:
                time.sleep(1)

if __name__ == "__main__":
    root = tk.Tk()
    app = ModbusClientApp(root)
    root.mainloop()
