import matplotlib.pyplot as plt
import numpy as np
import re

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def read_phase_data(filename, variable_name):
    """
    读取数据文件，自动检测编码
    支持格式: [变量名]:-79.70° 或 -79.70°
    """
    phases = []
    
    # 尝试不同的编码格式
    encodings = ['utf-8', 'gbk', 'gb2312', 'ascii', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(filename, 'r', encoding=encoding) as file:
                print(f"使用 {encoding} 编码成功读取文件")
                for line in file:
                    line = line.strip()
                    if line:
                        # 使用正则表达式提取数值
                        patterns = [
                            rf'{variable_name}:\s*(-?\d+\.?\d*)°?',  # 变量名:-79.70°
                            rf'{variable_name}:\s*(-?\d+\.?\d*)',    # 变量名:-79.70
                            r'(-?\d+\.?\d*)°',                       # -79.70°
                            r'(-?\d+\.?\d*)'                         # -79.70
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, line)
                            if match:
                                phase_value = float(match.group(1))
                                phases.append(phase_value)
                                break
                break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"使用 {encoding} 编码时出现错误: {e}")
            continue
    
    return phases

def create_trend_plot(phases, filename, height, width):
    """
    创建美观的折线图显示相位变化趋势
    """
    # 创建图表
    plt.figure(figsize=(width, height))
    
    # 数据点序号
    x = np.arange(1, len(phases) + 1)
    
    # 绘制主折线图
    plt.plot(x, phases, linewidth=2.5, marker='o', markersize=6, 
             color='#1f77b4', markerfacecolor='#ff7f0e', 
             markeredgewidth=1, markeredgecolor='white', alpha=0.9,
             label='相位数据')
    
    # 添加趋势线
    # if len(phases) > 1:
    #     z = np.polyfit(x, phases, 1)  # 线性拟合
    #     p = np.poly1d(z)
    #     plt.plot(x, p(x), "--", color='red', linewidth=2, alpha=0.8, 
    #             label=f'趋势线 (斜率: {z[0]:.3f}°/点)')
    
    # 添加网格
    plt.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # 设置标题和标签
    plt.title(f'相位数据变化趋势图\n', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('数据点序号', fontsize=12)
    plt.ylabel('相位 (度)', fontsize=12)
    
    # 添加统计信息
    # mean_val = np.mean(phases)
    # std_val = np.std(phases)
    # plt.axhline(y=mean_val, color='green', linestyle=':', linewidth=2, alpha=0.7,
    #            label=f'平均值: {mean_val:.2f}°')
    
    # 填充标准差区域
    # plt.fill_between(x, mean_val - std_val, mean_val + std_val, 
    #                 alpha=0.2, color='green', 
    #                 label=f'±1标准差区域 (σ={std_val:.2f}°)')
    
    # 标注最值点
    # max_idx = np.argmax(phases)
    # min_idx = np.argmin(phases)
    
    # plt.annotate(f'最大值\n{phases[max_idx]:.2f}°', 
    #             xy=(x[max_idx], phases[max_idx]), 
    #             xytext=(10, 20), textcoords='offset points',
    #             bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
    #             arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
    
    # plt.annotate(f'最小值\n{phases[min_idx]:.2f}°', 
    #             xy=(x[min_idx], phases[min_idx]), 
    #             xytext=(10, -30), textcoords='offset points',
    #             bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.7),
    #             arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
    
    # 设置图例
    # plt.legend(loc='upper right', framealpha=0.9)
    
    # 美化坐标轴
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['left'].set_linewidth(0.5)
    plt.gca().spines['bottom'].set_linewidth(0.5)
    
    # 设置坐标轴范围，留出适当边距
    y_margin = (max(phases) - min(phases)) * 0.1
    plt.ylim(min(phases) - y_margin, max(phases) + y_margin)
    plt.xlim(0.5, len(phases) + 0.5)
    
    # 调整布局
    plt.tight_layout()
    
    return plt.gcf()

def main(filename, height, width):
    try:
        # 获取变量名
        variable_name = input("请输入变量名(如Phase): ")
        
        # 读取数据
        phases = read_phase_data(filename, variable_name)
        
        if not phases:
            print(f"未找到有效的{variable_name}数据，请检查文件格式")
            print("支持的格式示例:")
            print(f"  {variable_name}:-79.70°")
            print(f"  {variable_name}:-79.70")
            print("  -79.70°")
            print("  -79.70")
            return
            
        print(f"成功读取 {len(phases)} 个{variable_name}数据点")
        print(f"数据范围: {min(phases):.2f}° 到 {max(phases):.2f}°")
        print(f"平均值: {np.mean(phases):.2f}°, 标准差: {np.std(phases):.2f}°")
        
        # 创建折线图
        fig = create_trend_plot(phases, filename, height, width)
        
        # 保存图片
        plt.savefig(f'{filename}_plot.png', dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        print("图表已保存")
        
        # 不显示图表，直接保存
        plt.close()
        print(f"图表已保存为: {filename}_plot.png")
        
    except FileNotFoundError:
        print(f"文件 '{filename}' 未找到，请检查文件路径")
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")

if __name__ == "__main__":

    # 提示用户输入文件名
    filename = input("请输入同一目录下的文件名: ")
    # 图表尺寸 - 请根据需要调整
    main(filename, height = 6, width = 24)