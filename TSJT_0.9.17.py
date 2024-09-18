import tkinter as tk
from tkinter import messagebox
import cv2
import numpy as np
import pyautogui
from PIL import Image, ImageTk, ImageGrab
import win32clipboard
import win32con
import io

# 全局变量
points = []
img = None
img_copy = None
fullscreen_window = None  # 用于全屏窗口的变量
corrected_image = None  # 用于保存矫正后的图片


# 捕获屏幕截图
def capture_screenshot():
    screenshot = pyautogui.screenshot()
    image = np.array(screenshot)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)  # 转换为BGR格式
    return image


# 在图片上画点
def draw_point(image, point, color=(255, 0, 0), radius=5):
    cv2.circle(image, point, radius, color, -1)


# 绘制多边形区域
def draw_polygon(image, points, color=(0, 255, 0), thickness=2, transparency=0.4):
    overlay = image.copy()  # 创建副本以绘制透明效果
    pts_np = np.array(points, dtype=np.int32)
    cv2.fillPoly(overlay, [pts_np], color)

    # 透明度控制
    cv2.addWeighted(overlay, transparency, image, 1 - transparency, 0, image)


# 显示图片的函数
def show_image(img, label):
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(img_rgb)
    img_tk = ImageTk.PhotoImage(img_pil)

    # 在 tkinter 中显示图像
    label.config(image=img_tk)
    label.image = img_tk  # 保持对图片的引用


# 计算并返回点的排序，确保左上、右上、右下、左下顺序
def order_points(pts):
    pts = np.array(pts, dtype="float32")

    # 计算中心点
    center = np.mean(pts, axis=0)

    # 按角度排序
    def angle_from_center(pt):
        return np.arctan2(pt[1] - center[1], pt[0] - center[0])

    sorted_pts = sorted(pts, key=angle_from_center)

    # 确定顺序
    tl = sorted_pts[0]
    br = sorted_pts[2]
    tr = sorted_pts[1]
    bl = sorted_pts[3]

    return [tl, tr, br, bl]


# 点击事件处理函数，在点击的位置显示一个点
def on_click(event):
    global img_copy
    if len(points) < 4:
        # 获取点击的坐标
        x, y = event.x, event.y
        points.append((x, y))

        # 在图像上绘制点击的点
        draw_point(img_copy, (x, y))
        draw_polygon(img_copy, points)  # 实时绘制围起来的区域
        show_image(img_copy, label_fullscreen)

        if len(points) == 4:
            # 四个点选完，提示
            messagebox.showinfo("信息", "已选择四个角！可以点击“矫正”进行透视矫正。")
    else:
        messagebox.showinfo("信息", "已经选择了四个角！请点击“矫正”进行透视矫正。")


# 透视矫正
def correct_perspective():
    global img, fullscreen_window, corrected_image
    if len(points) != 4:
        messagebox.showerror("错误", "请先选择四个角！")
        return

    # 排序点
    sorted_points = order_points(points)

    # 定义透视变换的点
    pts1 = np.float32(sorted_points)

    # 计算宽和高
    width = int(max(np.linalg.norm(pts1[0] - pts1[1]), np.linalg.norm(pts1[2] - pts1[3])) + 1)
    height = int(max(np.linalg.norm(pts1[0] - pts1[3]), np.linalg.norm(pts1[1] - pts1[2])) + 1)

    # 定义目标区域的四个顶点
    pts2 = np.float32([[0, 0], [width, 0], [width, height], [0, height]])

    # 计算透视变换矩阵
    matrix = cv2.getPerspectiveTransform(pts1, pts2)

    # 进行透视变换
    corrected_image = cv2.warpPerspective(img, matrix, (width, height))

    # 显示结果并关闭全屏窗口
    show_image(corrected_image, label_img)
    fullscreen_window.destroy()  # 关闭全屏窗口


# 将图像复制到剪切板
def copy_to_clipboard():
    global corrected_image
    if corrected_image is None:
        messagebox.showerror("错误", "没有可复制的图像！")
        return

    # 创建位图对象
    bmp = Image.new('RGBA', corrected_image.shape[1::-1], (255, 255, 255, 0))
    bmp.paste(Image.fromarray(cv2.cvtColor(corrected_image, cv2.COLOR_BGR2RGB)))

    # 将位图对象复制到剪切板中
    output = io.BytesIO()
    bmp.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]  # 跳过BMP头信息
    output.close()

    # 将数据复制到剪切板
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_DIB, data)
    win32clipboard.CloseClipboard()

    # 显示成功消息
    show_timed_message("图像已复制到剪切板！")


# 自定义消息框
def show_timed_message(msg):
    msg_window = tk.Toplevel(root)
    msg_window.title("信息")
    label_msg = tk.Label(msg_window, text=msg)
    label_msg.pack(pady=10)

    # 设置定时器0.5秒后关闭消息框
    msg_window.after(500, msg_window.destroy)

# 开始截图并显示全屏窗口
def start_screenshot():
    global img, img_copy, points, fullscreen_window, label_fullscreen
    points.clear()  # 每次开始前重置四个角
    img = capture_screenshot()  # 捕获截图
    img_copy = img.copy()  # 保留一个副本用于绘制

    # 创建全屏窗口
    fullscreen_window = tk.Toplevel(root)
    fullscreen_window.attributes('-fullscreen', True)  # 设置全屏
    fullscreen_window.bind("<Escape>", lambda e: fullscreen_window.destroy())  # ESC键退出全屏

    # 显示截图
    label_fullscreen = tk.Label(fullscreen_window)
    label_fullscreen.pack(expand=True, fill=tk.BOTH)
    show_image(img_copy, label_fullscreen)

    # 绑定点击事件到全屏窗口
    label_fullscreen.bind("<Button-1>", on_click)


# 初始化 Tkinter 窗口
root = tk.Tk()
root.title("透视裁切工具")

# 创建窗口布局
label = tk.Label(root, text="点击按钮进行操作")
label.pack(pady=10)

btn_capture = tk.Button(root, text="截图", command=start_screenshot)
btn_capture.pack(pady=5)

btn_correct = tk.Button(root, text="矫正", command=correct_perspective)
btn_correct.pack(pady=5)

btn_copy = tk.Button(root, text="复制", command=copy_to_clipboard)
btn_copy.pack(pady=5)

# 用于显示处理后的图片
label_img = tk.Label(root)
label_img.pack(pady=10)

# 运行 Tkinter 主循环
root.mainloop()
