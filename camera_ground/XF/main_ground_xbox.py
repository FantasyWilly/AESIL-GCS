#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File   : main_ground_xbox.py
Author : FantasyWilly   
Email  : bc697522h04@gmail.com  
SPDX-License-Identifier: Apache-2.0 

開發公司:
    • 先飛科技 (XF)

功能總覽:
    • 地面端透過 Xbox 控制器發送控制命令

遵循:
    • Google Python Style Guide (含區段標題)
    • PEP 8 (行寬 ≤ 88, snake_case, 2 空行區段分隔)
"""

# ------------------------------------------------------------------------------------ #
# Imports
# ------------------------------------------------------------------------------------ #
# 標準庫
import time
import sys
import pygame

# 第三方套件
import cv2

# 專案內部模組
import camera_command as cm
from gcu_controller import GCUController


# ------------------------------------------------------------------------------------ #
# TCP 連線 <IP:Port> 
# ------------------------------------------------------------------------------------ #
DEVICE_IP = "192.168.50.73"     # Server IP
DEVICE_PORT = 9999                # Server Port 


# ------------------------------------------------------------------------------------ #
# 影像串流 <CAMERA_URL>
# ------------------------------------------------------------------------------------ #
CAMERA_URL  = 'rtsp://192.168.50.73:8554/live/stream'


# ------------------------------------------------------------------------------------ #
# 每次 Gimbal 每步移動度數
# ------------------------------------------------------------------------------------ #
CONTROL_INCREMENT = 5.0           # 雲台角度增量 (預設 5 度)


# ------------------------------------------------------------------------------------ #
# xbox 傳輸控制指令
# ------------------------------------------------------------------------------------ #
def xbox_controller_loop(controller: GCUController) -> None:

    # 初始化 xbox 搖桿
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("未找到 Xbox 控制器")
        sys.exit(1)

    # 取得第一個連接的控制器並初始化
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print("Xbox 控制器已啟動")

    # 初始化 Laser 開關旗標
    laser_enabled = False

    while True:
        for event in pygame.event.get():

            # 按鍵 - [A, B, X, Y, L, R]  
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == 7:
                    print("按下按鈕 7, 程式將結束")
                    pygame.quit()
                    return
  
                if joystick.get_button(0):
                    print("A 按鈕按下：向下")
                    cm.down(controller)
                elif joystick.get_button(1):
                    print("B 按鈕按下：拍照")
                    cm.photo(controller)
                elif joystick.get_button(2):
                    print("X 按鈕按下：錄影")
                    cm.video(controller)
                elif joystick.get_button(3):
                    print("Y 按鈕按下：回中")
                    cm.reset(controller)
                elif joystick.get_button(4):
                    print("L 按鈕按下：鎖定")
                    cm.lock(controller)
                elif joystick.get_button(5):
                    print("R 按鈕按下：跟隨")
                    cm.follow(controller)

            # 按鍵 - [選單, 目錄]  
            if event.type == pygame.JOYBUTTONDOWN:
                if joystick.get_button(6):
                    # print("校準")
                    cm.calibration(controller)
                elif joystick.get_button(7):
                    # print("聚焦")
                    cm.focus(controller)
                elif joystick.get_button(11):
                    laser_enabled = not laser_enabled

                    if laser_enabled:
                        cm.laser_on(controller)
                        # print("Laser ON")
                    else:
                        cm.laser_off(controller)
                        # print("Laser OFF")

            # 按鍵 - [上下左右]   
            elif event.type == pygame.JOYHATMOTION:
                hat = joystick.get_hat(0)
                if hat != (0, 0):
                    pitch = hat[1] * CONTROL_INCREMENT
                    yaw   = hat[0] * CONTROL_INCREMENT
                    print(f"發送雲台控制指令 -> pitch: {pitch}°, yaw: {yaw}°")
                    cm.control_gimbal(controller, pitch=pitch, yaw=yaw)
            
            # 按鍵 - [右扳機 (RT) - 5], [左扳機 (LT) - 4] - Windows
            # 按鍵 - [右扳機 (RT) - 5], [左扳機 (LT) - 2] - Linux
            elif event.type == pygame.JOYAXISMOTION:
                if event.axis == 5:
                    rt_value = joystick.get_axis(5)
                    if rt_value > 0.5:
                        print("RT 按下：放大")
                        cm.zoom_in(controller)
                    else:
                        print("RT 釋放：停止放大縮小")
                        cm.zoom_stop(controller)
                elif event.axis == 4:
                    lt_value = joystick.get_axis(4)
                    if lt_value > 0.5:
                        print("LT 按下：縮小")
                        cm.zoom_out(controller)
                    else:
                        print("LT 釋放：停止放大縮小")
                        cm.zoom_stop(controller)
        time.sleep(0.1)

# ------------------------------------------------------------------------------------ #
# 主程式
# ------------------------------------------------------------------------------------ #
def main() -> None:
    """
    - 說明 [main]
        1. 創建 [GCUController] 並 連線至 GCU控制盒
        2. 動態獲取 畫面像素大小
        3. Xbox 搖桿控制
    """

    # 動態獲取 CAMERA_URL 串流影像大小
    cap = cv2.VideoCapture(CAMERA_URL)
    if not cap.isOpened():
        print(f"[CAMERA_URL] 無法連接到串流: {CAMERA_URL}")
        width = height = 0
    else:
        width   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        print(f"[CAMERA_URL] 畫面大小: {width}x{height}")

    # 建立 TCP 連線物件 - [GCUController]
    controller = GCUController(DEVICE_IP, DEVICE_PORT, width, height)

    try:
        # 1. TCP 連線
        controller.connect()
        print("[連線] 嵌入式電腦")

        # 2. 開啟 Xbox 遙控控制        
        xbox_controller_loop(controller)
        
    except Exception as e:
        print("[main] 出現錯誤:", e)
    finally:
        controller.disconnect()
        print("連線已關閉")

if __name__ == "__main__":
    main()
