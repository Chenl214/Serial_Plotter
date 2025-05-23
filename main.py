import serial
import threading
import traceback  # 添加traceback模块
from matplotlib.animation import FuncAnimation
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # 添加Tkinter后端支持
import numpy as np

import serial.tools.list_ports
import matplotlib.pyplot as plt
import time

class SerialPlotter:
    def __init__(self):
        self.ser = None
        self.running = False
        self.data_dict = {}
        self.selected_params = []
        self.lock = threading.Lock()
        
        # 初始化主窗口
        self.root = tk.Tk()
        self.root.title("串口数据实时绘图")
        
        # 设置窗口最小尺寸和初始尺寸
        self.root.minsize(800, 500)
        self.root.geometry("800x500")
        
        # 初始化变量
        self.port_var = tk.StringVar()
        self.baud_var = tk.StringVar()
        self.zero_line_var = tk.BooleanVar()
        self.data_points_var = tk.IntVar(value=5)
        self.paused = False
        self.pause_lock = threading.Lock()
        
        # 数据统计变量
        self.data_count = 0
        self.last_count = 0
        self.last_count_time = time.time()
        
        # 创建UI组件
        self.create_widgets()
        
        # 确保窗口关闭时正确清理资源
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 启动状态更新定时器
        self.update_status()
        
        # 启动主循环
        self.root.mainloop()
        
    def refresh_ports(self):
        """刷新可用串口列表"""
        try:
            # 获取当前选择的串口
            current_port = self.port_var.get()
            
            # 获取可用串口列表
            ports = [port.device for port in serial.tools.list_ports.comports()]
            
            # 更新下拉列表
            self.port_combo['values'] = ports
            
            # 如果当前选择的串口仍然可用，保持选择
            if current_port in ports:
                self.port_var.set(current_port)
            else:
                # 否则选择第一个可用串口
                self.port_var.set(ports[0] if ports else "")
            
            # 更新状态
            self.status_var.set(f"已刷新串口列表，发现 {len(ports)} 个串口")
            print(f"可用串口: {ports}")
            
        except Exception as e:
            self.status_var.set(f"刷新串口失败: {str(e)}")
            print(f"刷新串口错误: {e}")
    
    def update_status(self):
        """更新状态栏信息"""
        try:
            # 计算数据接收速率
            current_time = time.time()
            elapsed = current_time - self.last_count_time
            
            if elapsed >= 1.0:  # 每秒更新一次
                data_rate = (self.data_count - self.last_count) / elapsed
                self.data_rate_var.set(f"{data_rate:.1f} 点/秒")
                
                self.last_count = self.data_count
                self.last_count_time = current_time
            
            # 更新运行状态
            if self.running:
                if self.paused:
                    status = "已暂停"
                else:
                    status = "正在监测"
                    
                # 添加数据点信息
                total_points = sum(len(data) for data in self.data_dict.values())
                status += f" - 共 {total_points} 个数据点"
                
                self.status_var.set(status)
        except Exception as e:
            print(f"状态更新错误: {e}")
        
        # 每100ms更新一次状态
        self.root.after(100, self.update_status)

    def create_widgets(self):
        # 设置整体样式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 顶部工具栏
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill='x', pady=(0, 5))
        
        # 添加刷新串口按钮
        refresh_btn = ttk.Button(toolbar_frame, text="刷新串口", command=self.refresh_ports)
        refresh_btn.pack(side='right', padx=5)

        # 串口设置区域
        port_frame = ttk.LabelFrame(main_frame, text=" 串口设置 ")
        port_frame.pack(fill='x', pady=5)
        
        # 串口选择
        ttk.Label(port_frame, text="串口:").grid(row=0, column=0, padx=5)
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.port_var, values=ports, width=20)
        self.port_combo.grid(row=0, column=1, padx=5)
        self.port_var.set(ports[0] if ports else "")

        # 波特率选择
        ttk.Label(port_frame, text="波特率:").grid(row=0, column=2, padx=5)
        self.baud_combo = ttk.Combobox(port_frame, textvariable=self.baud_var, 
                                     values=["9600", "19200", "38400", "57600", "115200"], width=10)
        self.baud_combo.grid(row=0, column=3, padx=5)
        self.baud_var.set("115200")

        # 参数输入区域
        param_frame = ttk.LabelFrame(main_frame, text=" 监测参数 ")
        param_frame.pack(fill='x', pady=5)
        
        ttk.Label(param_frame, text="参数(逗号分隔):").grid(row=0, column=0, padx=5)
        self.param_entry = ttk.Entry(param_frame)
        self.param_entry.grid(row=0, column=1, columnspan=3, sticky='ew', padx=5)

        # 显示设置区域
        settings_frame = ttk.LabelFrame(main_frame, text=" 显示设置 ")
        settings_frame.pack(fill='x', pady=5)
        
        ttk.Checkbutton(settings_frame, text="显示0轴", variable=self.zero_line_var).pack(side='left', padx=10)
        ttk.Label(settings_frame, text="保留数据点(百):").pack(side='left', padx=5)
        self.data_points_entry = ttk.Entry(settings_frame, textvariable=self.data_points_var, width=5)
        self.data_points_entry.pack(side='left', padx=5)
        self.data_points_var.set(5)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        self.start_btn = ttk.Button(btn_frame, text="开始", command=self.start)
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="停止", command=self.stop, state="disabled")
        self.stop_btn.pack(side='left', padx=5)
        
        self.pause_btn = ttk.Button(btn_frame, text="暂停", command=self.toggle_pause, state="disabled")
        self.pause_btn.pack(side='left', padx=5)
        
        self.refresh_btn = ttk.Button(btn_frame, text="刷新", command=self.refresh_data, state="disabled")
        self.refresh_btn.pack(side='left', padx=5)
        
        # 添加状态栏
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill='x', side='bottom', padx=5, pady=5)
        
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor='w')
        status_label.pack(side='left', fill='x', expand=True)
        
        self.data_rate_var = tk.StringVar(value="0 点/秒")
        data_rate_label = ttk.Label(status_frame, textvariable=self.data_rate_var)
        data_rate_label.pack(side='right')

    def start(self):
        port = self.port_var.get()
        baud = int(self.baud_var.get())
        params = self.param_entry.get().strip()
        if not port or not params:
            self.status_var.set("错误：请填写串口和参数")
            messagebox.showerror("错误", "请填写串口和参数")
            return
            
        try:
            # 清除之前的图表
            if hasattr(self, 'fig'):
                plt.close(self.fig)
                
                # 移除之前的绘图框架
                for widget in self.root.winfo_children():
                    if isinstance(widget, ttk.Frame) and widget != self.root.nametowidget('.!frame'):
                        widget.destroy()
            
            # 初始化参数和数据
            self.selected_params = [p.strip() for p in params.split(",") if p.strip()]
            self.data_dict = {p: [] for p in self.selected_params}
            
            # 重置数据统计
            self.data_count = 0
            self.last_count = 0
            self.last_count_time = time.time()
            
            # 检查窗口是否最大化，如果不是则最大化
            if self.root.state() != 'zoomed':
                self.root.state('zoomed')
                print("窗口已最大化")
            
            # 更新状态栏
            self.status_var.set(f"正在连接串口 {port}...")
            self.root.update_idletasks()
            
            # 打开串口
            self.ser = serial.Serial(port, baud, timeout=0.5)
            
            # 更新UI状态
            self.running = True
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.pause_btn.config(state="normal")
            self.refresh_btn.config(state="normal")  # 启用刷新按钮
            
            # 先显示绘图窗口
            self.show_plot()
            
            # 启动串口读取线程
            self.thread = threading.Thread(target=self.read_serial, daemon=True)
            self.thread.start()
            
            # 更新状态栏
            self.status_var.set(f"正在监测 - 串口:{port} 波特率:{baud}")
            self.data_rate_var.set("0.0 点/秒")
            
            # 添加调试信息
            print(f"串口监测已启动 - 参数: {self.selected_params}")
            print(f"串口状态: {'已打开' if self.ser.is_open else '未打开'}")
            print(f"线程状态: {'运行中' if self.thread.is_alive() else '未启动'}")
            
            # 强制刷新窗口
            self.root.update_idletasks()
            
        except Exception as e:
            self.running = False
            messagebox.showerror("启动错误", f"无法启动监测: {str(e)}")
            print(f"启动失败: {traceback.format_exc()}")
            
            # 恢复UI状态
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.pause_btn.config(state="disabled")

    def stop(self):
        self.running = False
        
        # 等待串口线程结束
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        # 关闭串口
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except:
                pass
            
        # 停止动画
        if hasattr(self, 'ani'):
            self.ani.event_source.stop()
            
        # 清除图表数据
        if hasattr(self, 'data_dict'):
            self.data_dict = {}
            
        # 清除图表
        if hasattr(self, 'fig'):
            plt.close(self.fig)
            self.fig = None
            
        # 移除绘图框架
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame) and widget != self.root.nametowidget('.!frame'):
                widget.destroy()
            
        # 更新UI状态
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.pause_btn.config(state="disabled")
        self.refresh_btn.config(state="disabled")  # 禁用刷新按钮
        
        # 强制刷新GUI
        self.root.update_idletasks()

    def on_close(self):
        self.stop()
        
        # 清理Matplotlib资源
        if hasattr(self, 'fig'):
            try:
                plt.close(self.fig)
            except:
                pass
                
        self.root.destroy()

    def read_serial(self):
        buffer = ""
        data_count = 0
        last_report_time = time.time()
        
        print("串口读取线程已启动")
        
        while self.running and self.ser and self.ser.is_open:
            with self.pause_lock:
                if self.paused:
                    time.sleep(0.1)
                    continue
            
            try:
                # 批量读取可用数据
                if self.ser.in_waiting > 0:
                    raw_data = self.ser.read(self.ser.in_waiting)
                    buffer += raw_data.decode('utf-8', errors='ignore')
                else:
                    # 没有数据时短暂休眠，减少CPU占用
                    time.sleep(0.01)
                    continue
                
                # 处理完整行
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 调试输出（每秒最多输出一次）
                    current_time = time.time()
                    if current_time - last_report_time > 1.0:
                        print(f"接收数据: {line}")
                        last_report_time = current_time
                    
                    # 优化数据解析
                    for param in self.selected_params:
                        if f"{param}:" in line:
                            try:
                                # 提取数值部分
                                value_part = line.split(f"{param}:")[1]
                                # 去除单位符号并提取数值
                                value_str = ''.join(c for c in value_part.split()[0] 
                                                  if c.isdigit() or c in '.-')
                                value = float(value_str)
                                
                                with self.lock:
                                    if param not in self.data_dict:
                                        self.data_dict[param] = []
                                    self.data_dict[param].append(value)
                                
                                # 更新数据统计
                                self.data_count += 1
                                data_count += 1
                                
                                # 每100个数据点输出一次日志
                                if data_count % 100 == 0:
                                    print(f"已处理 {data_count} 个数据点")
                                    
                            except (ValueError, IndexError, AttributeError) as e:
                                print(f"数据解析错误: {line} - {e}")
                                continue
                                
            except serial.SerialException as e:
                print(f"串口错误: {e}")
                # 尝试重新连接
                try:
                    if self.ser:
                        self.ser.close()
                    time.sleep(1)
                    self.ser = serial.Serial(self.port_var.get(), int(self.baud_var.get()), timeout=0.5)
                    print("串口已重新连接")
                except:
                    print("重连失败，停止读取")
                    self.stop()
                    break
            except Exception as e:
                print(f"数据处理错误: {e}")
                traceback.print_exc()
                continue

    # 图形样式优化
    def show_plot(self):
        # 移除之前的绘图框架（如果存在）
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame) and widget != self.root.nametowidget('.!frame'):
                widget.destroy()
                
        # 创建新的绘图框架
        plot_frame = ttk.Frame(self.root)
        plot_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 设置绘图样式
        plt.style.use('ggplot')
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建图形和坐标轴
        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.1)
        
        # 设置标题和标签
        self.ax.set_title('串口数据实时监测', fontsize=12, pad=10)
        self.ax.set_xlabel('数据点索引', fontsize=10)
        self.ax.set_ylabel('数值', fontsize=10)
        
        # 创建canvas并嵌入到Tkinter窗口
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # 初始化数据线
        self.lines = {}
        colors = plt.cm.rainbow(np.linspace(0, 1, len(self.selected_params)))
        for param, color in zip(self.selected_params, colors):
            line, = self.ax.plot([], [], label=param, color=color, lw=1.5)
            self.lines[param] = line
        
        # 添加图例
        self.ax.legend(loc='upper right', fontsize=8)
        
        # 设置网格
        self.ax.grid(True, linestyle='--', alpha=0.6)
        
        # 设置初始范围
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(-1, 1)
        
        # 根据选项添加0轴
        if self.zero_line_var.get():
            self.ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        
        # 设置窗口缩放支持
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # 添加鼠标移动事件处理
        self.annotation = self.ax.annotate("", xy=(0,0), xytext=(20,20), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"),
                            arrowprops=dict(arrowstyle="->"))
        self.annotation.set_visible(False)
        
        # 用于存储高亮点
        self.highlight_points = {param: None for param in self.selected_params}
        
        def on_motion(event):
            if event.inaxes == self.ax:
                visible = False
                for param, line in self.lines.items():
                    xdata, ydata = line.get_data()
                    if len(xdata) > 0:
                        # 找到最近的点
                        x_index = min(range(len(xdata)), key=lambda i: abs(xdata[i] - event.xdata))
                        y_value = ydata[x_index]
                        # 如果鼠标在点附近
                        if abs(event.xdata - xdata[x_index]) < 0.1 and abs(event.ydata - y_value) < 0.1:
                            # 显示注释
                            self.annotation.xy = (xdata[x_index], y_value)
                            self.annotation.set_text(f"{y_value:.2f}")
                            self.annotation.set_visible(True)
                            visible = True
                            
                            # 清除之前的高亮点
                            if self.highlight_points[param]:
                                self.highlight_points[param].remove()
                            
                            # 绘制新的高亮点
                            self.highlight_points[param] = self.ax.plot(
                                xdata[x_index], y_value, 'o', 
                                color=line.get_color(),
                                markersize=10,
                                alpha=0.5
                            )[0]
                            break
                        else:
                            # 如果不在点附近，清除高亮点
                            if self.highlight_points[param]:
                                self.highlight_points[param].remove()
                                self.highlight_points[param] = None
                if not visible:
                    self.annotation.set_visible(False)
                self.fig.canvas.draw_idle()
        
        self.fig.canvas.mpl_connect("motion_notify_event", on_motion)
        
        # 启动动画
        self.ani = FuncAnimation(
            self.fig,
            self.update_plot,
            interval=50,  # 20fps
            blit=False,
            cache_frame_data=False
        )
        
        # 禁用Matplotlib的默认工具栏
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        try:
            self.canvas.toolbar.pack_forget()
        except:
            pass
        
        # 打印调试信息
        print("创建图形窗口完成")
        print(f"当前Matplotlib后端: {plt.get_backend()}")
        print(f"动画已启动，更新间隔: 50ms")
        
        # 强制更新布局
        self.fig.tight_layout()
        self.canvas.draw()

    def update_plot(self, frame):
        try:
            with self.pause_lock:
                if self.paused:
                    return []
            
            # 更新频率控制
            current_time = time.time()
            if hasattr(self, 'last_update'):
                if current_time - self.last_update < 0.05:  # 限制20fps
                    return []
            self.last_update = current_time
            
            # 快照方式获取数据，减少锁持有时间
            with self.lock:
                data_snapshot = {}
                max_points = self.data_points_var.get() * 100
                for param in self.selected_params:
                    data = self.data_dict.get(param, [])
                    if len(data) > max_points:
                        self.data_dict[param] = data[-max_points:]
                    data_snapshot[param] = data[-max_points:]
            
            # 更新数据线
            has_new_data = False
            y_min, y_max = float('inf'), float('-inf')
            
            for param, data in data_snapshot.items():
                if data:
                    x_data = list(range(len(data)))
                    self.lines[param].set_data(x_data, data)
                    has_new_data = True
                    
                    # 更新Y轴范围
                    y_min = min(y_min, min(data))
                    y_max = max(y_max, max(data))
            
            # 只在有新数据时更新视图
            if has_new_data:
                # 设置X轴范围
                x_max = max(100, max(len(data) for data in data_snapshot.values()))
                self.ax.set_xlim(-5, x_max + 5)
                
                # 设置Y轴范围（添加边距）
                if y_min != float('inf'):
                    y_range = y_max - y_min
                    margin = y_range * 0.1 if y_range != 0 else 0.5
                    self.ax.set_ylim(y_min - margin, y_max + margin)
                
                # 高效更新画布
                self.canvas.draw_idle()
                self.canvas.flush_events()
                
                # 打印调试信息（每100帧打印一次）
                if frame % 100 == 0:
                    print(f"更新帧: {frame}, 数据点数: {x_max}")
            
            return []
            
        except Exception as e:
            print(f"更新错误: {e}")
            traceback.print_exc()
            return []

    def run(self):
        self.root.mainloop()

    def refresh_data(self):
        """刷新数据，清空图表并重新开始计数"""
        if not self.running:
            return
            
        with self.lock:
            # 清空数据字典
            for param in self.selected_params:
                self.data_dict[param] = []
                
            # 重置计数器
            self.data_count = 0
            self.last_count = 0
            self.last_count_time = time.time()
            
            # 重置图表
            for line in self.lines.values():
                line.set_data([], [])
                
            # 重置坐标轴范围
            self.ax.set_xlim(0, 100)
            self.ax.set_ylim(-1, 1)
            self.canvas.draw_idle()
            
            # 更新状态
            self.status_var.set("数据已刷新 - 正在监测")
            self.data_rate_var.set("0.0 点/秒")
            
        print("数据已刷新，重新开始计数")

    def toggle_pause(self):
        # 添加线程安全的状态切换
        with self.pause_lock:
            self.paused = not self.paused
            new_text = "继续" if self.paused else "暂停"
            self.pause_btn.config(text=new_text)
        
        # 强制刷新GUI
        self.root.update_idletasks()

if __name__ == "__main__":
    SerialPlotter().run()