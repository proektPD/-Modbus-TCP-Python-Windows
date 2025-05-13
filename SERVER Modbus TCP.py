from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

import threading
import random
import time
from tkinter import *
from tkinter import messagebox, simpledialog

# Имитируемое устройство - "Датчик давления PT-100"
class VirtualDevice:
    def __init__(self):
        self.coils = [False] * 10  # Дискретные выходы (10 штук)
        self.discrete_inputs = [False] * 10  # Дискретные входы (10 штук)
        self.holding_registers = [0] * 20  # Регистры хранения (20 штук)
        self.input_registers = [0] * 20  # Входные регистры (20 штук)
        
        # Инициализация начальных значений
        for i in range(10):
            self.coils[i] = random.choice([True, False])
            self.discrete_inputs[i] = random.choice([True, False])
            
        for i in range(20):
            self.holding_registers[i] = random.randint(0, 20)
            self.input_registers[i] = random.randint(0, 20)
    
    def update_values(self):
        """Обновление значений для имитации работы устройства"""
        # Случайное изменение значений
        for i in range(10):
            if random.random() > 0.8:  # 20% вероятность изменения
                self.coils[i] = not self.coils[i]
            if random.random() > 0.8:
                self.discrete_inputs[i] = not self.discrete_inputs[i]
                
        for i in range(20):
            if random.random() > 0.8:
                self.holding_registers[i] = max(0, min(20, self.holding_registers[i] + random.randint(-2, 2)))
            if random.random() > 0.8:
                self.input_registers[i] = max(0, min(20, self.input_registers[i] + random.randint(-2, 2)))

class ModbusServerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modbus TCP Сервер - Датчик PT-100")
        
        # Создаем виртуальное устройство
        self.device = VirtualDevice()
        
        # Флаг работы сервера
        self.server_running = False
        self.server_thread = None
        
        # Создаем GUI
        self.create_widgets()
        
        # Запускаем обновление значений устройства
        self.update_device_values()
    
    def create_widgets(self):
        """Создание интерфейса сервера"""
        # Основные параметры
        Label(self.root, text="Настройки сервера").grid(row=0, column=0, columnspan=2, pady=5)
        
        Label(self.root, text="IP адрес:").grid(row=1, column=0, sticky=W, padx=5)
        self.ip_entry = Entry(self.root)
        self.ip_entry.grid(row=1, column=1, padx=5)
        self.ip_entry.insert(0, "127.0.0.1")
        
        Label(self.root, text="Порт:").grid(row=2, column=0, sticky=W, padx=5)
        self.port_entry = Entry(self.root)
        self.port_entry.grid(row=2, column=1, padx=5)
        self.port_entry.insert(0, "5020")
        
        # Кнопки управления
        self.start_button = Button(self.root, text="Запустить сервер", command=self.start_server)
        self.start_button.grid(row=3, column=0, pady=10, padx=5)
        
        self.stop_button = Button(self.root, text="Остановить сервер", command=self.stop_server, state=DISABLED)
        self.stop_button.grid(row=3, column=1, pady=10, padx=5)
        
        # Статус сервера
        self.status_label = Label(self.root, text="Сервер остановлен", fg="red")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=5)
        
        # Имитация устройства
        Label(self.root, text="Имитация устройства Датчик PT-100").grid(row=5, column=0, columnspan=2, pady=5)
        
        # Таблица с текущими значениями
        self.create_values_table()
    
    def create_values_table(self):
        """Создание таблицы с текущими значениями регистров"""
        # Фрейм для таблицы
        table_frame = Frame(self.root)
        table_frame.grid(row=6, column=0, columnspan=2, padx=5, pady=5)
        
        # Заголовки
        Label(table_frame, text="Тип", relief=RIDGE, width=15).grid(row=0, column=0)
        Label(table_frame, text="Значение", relief=RIDGE, width=15).grid(row=0, column=1)
        
        # Отображение значений
        self.value_labels = {}
        
        # Coils (дискретные выходы)
        Label(table_frame, text="Coils", relief=RIDGE, width=15).grid(row=1, column=0, sticky=W+E)
        for i in range(5):  # Покажем только первые 5 для компактности
            self.value_labels[f"coil_{i}"] = Label(table_frame, text=str(self.device.coils[i]), relief=RIDGE, width=15)
            self.value_labels[f"coil_{i}"].grid(row=1, column=1+i)
        
        # Discrete Inputs (дискретные входы)
        Label(table_frame, text="Discrete Inputs", relief=RIDGE, width=15).grid(row=2, column=0, sticky=W+E)
        for i in range(5):
            self.value_labels[f"di_{i}"] = Label(table_frame, text=str(self.device.discrete_inputs[i]), relief=RIDGE, width=15)
            self.value_labels[f"di_{i}"].grid(row=2, column=1+i)
        
        # Holding Registers (регистры хранения)
        Label(table_frame, text="Holding Registers", relief=RIDGE, width=15).grid(row=3, column=0, sticky=W+E)
        for i in range(5):
            self.value_labels[f"hr_{i}"] = Label(table_frame, text=str(self.device.holding_registers[i]), relief=RIDGE, width=15)
            self.value_labels[f"hr_{i}"].grid(row=3, column=1+i)
        
        # Input Registers (входные регистры)
        Label(table_frame, text="Input Registers", relief=RIDGE, width=15).grid(row=4, column=0, sticky=W+E)
        for i in range(5):
            self.value_labels[f"ir_{i}"] = Label(table_frame, text=str(self.device.input_registers[i]), relief=RIDGE, width=15)
            self.value_labels[f"ir_{i}"].grid(row=4, column=1+i)
        
        # Кнопка для изменения значений
        Button(self.root, text="Изменить значение регистра", command=self.change_register_value).grid(row=8, column=0, columnspan=2, pady=5)
    
    def update_values_display(self):
        """Обновление отображения значений"""
        for i in range(5):
            self.value_labels[f"coil_{i}"].config(text=str(self.device.coils[i]))
            self.value_labels[f"di_{i}"].config(text=str(self.device.discrete_inputs[i]))
            self.value_labels[f"hr_{i}"].config(text=str(self.device.holding_registers[i]))
            self.value_labels[f"ir_{i}"].config(text=str(self.device.input_registers[i]))
    
    def change_register_value(self):
        """Изменение значения регистра вручную"""
        # Диалоговое окно для выбора типа регистра
        reg_type = simpledialog.askstring("Тип регистра", 
                                         "Введите тип регистра (coil, di, hr, ir):",
                                         parent=self.root)
        if not reg_type or reg_type.lower() not in ['coil', 'di', 'hr', 'ir']:
            messagebox.showerror("Ошибка", "Неверный тип регистра")
            return
        
        # Диалоговое окно для выбора адреса
        address = simpledialog.askinteger("Адрес регистра", 
                                        "Введите адрес регистра (0-19):",
                                        parent=self.root,
                                        minvalue=0, maxvalue=19)
        if address is None:
            return
        
        # Диалоговое окно для ввода значения
        if reg_type in ['coil', 'di']:
            value = simpledialog.askinteger("Значение", 
                                          "Введите значение (0 или 1):",
                                          parent=self.root,
                                          minvalue=0, maxvalue=1)
            value = bool(value)
        else:
            value = simpledialog.askinteger("Значение", 
                                          "Введите значение (0-20):",
                                          parent=self.root,
                                          minvalue=0, maxvalue=20)
        
        if value is None:
            return
        
        # Устанавливаем значение
        if reg_type == 'coil':
            self.device.coils[address] = value
        elif reg_type == 'di':
            self.device.discrete_inputs[address] = value
        elif reg_type == 'hr':
            self.device.holding_registers[address] = value
        elif reg_type == 'ir':
            self.device.input_registers[address] = value
        
        self.update_values_display()
        messagebox.showinfo("Успех", "Значение регистра изменено")
    
    def update_device_values(self):
        """Периодическое обновление значений устройства"""
        if self.server_running:
            self.device.update_values()
            self.update_values_display()
        
        # Планируем следующее обновление через 1 секунду
        self.root.after(1000, self.update_device_values)
    
    def run_modbus_server(self):
        """Запуск Modbus сервера в отдельном потоке"""
        # Создаем datastore с текущими значениями из устройства
        store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [int(x) for x in self.device.discrete_inputs]),
            co=ModbusSequentialDataBlock(0, [int(x) for x in self.device.coils]),
            hr=ModbusSequentialDataBlock(0, self.device.holding_registers),
            ir=ModbusSequentialDataBlock(0, self.device.input_registers),
        )
        
        context = ModbusServerContext(slaves=store, single=True)
        
        # Параметры сервера
        ip = self.ip_entry.get()
        port = int(self.port_entry.get())
        
        # Запуск сервера
        self.server_running = True
        StartTcpServer(context=context, address=(ip, port))
    
    def start_server(self):
        """Запуск сервера"""
        if not self.server_running:
            self.server_thread = threading.Thread(target=self.run_modbus_server, daemon=True)
            self.server_thread.start()
            
            self.start_button.config(state=DISABLED)
            self.stop_button.config(state=NORMAL)
            self.status_label.config(text="Сервер запущен", fg="green")
            
            messagebox.showinfo("Сервер", "Modbus сервер запущен")
    
    def stop_server(self):
        """Остановка сервера с проверкой пароля"""
        # Запрос пароля для отключения
        password = simpledialog.askstring("Пароль", 
                                        "Введите пароль для отключения сервера:",
                                        parent=self.root,
                                        show='*')
        
        if password == "modbus":  # Простой пароль для демонстрации
            self.server_running = False
            
            self.start_button.config(state=NORMAL)
            self.stop_button.config(state=DISABLED)
            self.status_label.config(text="Сервер остановлен", fg="red")
            
            messagebox.showinfo("Сервер", "Modbus сервер остановлен")
        else:
            messagebox.showerror("Ошибка", "Неверный пароль")

if __name__ == "__main__":
    root = Tk()
    app = ModbusServerApp(root)
    root.mainloop()
