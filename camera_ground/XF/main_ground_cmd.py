#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File   : main_ground_cmd.py
Author : FantasyWilly   
Email  : bc697522h04@gmail.com  
SPDX-License-Identifier: Apache-2.0 

開發公司:
    • 先飛科技 (XF)

功能總覽:
    • 地面端透過 CMD 發送控制命令

遵循:
    • Google Python Style Guide (含區段標題)
    • PEP 8 (行寬 ≤ 88, snake_case, 2 空行區段分隔)
"""

# ------------------------------------------------------------------------------------ #
# Imports
# ------------------------------------------------------------------------------------ #
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
# CMD 指令控制
# ------------------------------------------------------------------------------------ #
def command_line_loop(controller: GCUController) -> None:
    """
    使用終端機輸入指令控制
    """

    print("\n=== 指令控制模式 ===")
    print("可用指令：")
    print("  down / photo / video / reset")
    print("  lock / follow / calibration / focus")
    print("  laser_on / laser_off")
    print("  zoom_in / zoom_out / zoom_stop")
    print("  gimbal <pitch> <yaw>  (例: gimbal 5 -5)")
    print("  exit\n")

    while True:
        try:
            cmd = input("請輸入指令 > ").strip().lower()

            if cmd == "exit":
                print("結束程式")
                return

            elif cmd == "down":
                cm.down(controller)

            elif cmd == "photo":
                cm.photo(controller)

            elif cmd == "video":
                cm.video(controller)

            elif cmd == "reset":
                cm.reset(controller)

            elif cmd == "lock":
                cm.lock(controller)

            elif cmd == "follow":
                cm.follow(controller)

            elif cmd == "calibration":
                cm.calibration(controller)

            elif cmd == "focus":
                cm.focus(controller)

            elif cmd == "laser_on":
                cm.laser_on(controller)

            elif cmd == "laser_off":
                cm.laser_off(controller)

            elif cmd == "zoom_in":
                cm.zoom_in(controller)

            elif cmd == "zoom_out":
                cm.zoom_out(controller)

            elif cmd == "zoom_stop":
                cm.zoom_stop(controller)

            elif cmd.startswith("gimbal"):
                parts = cmd.split()
                if len(parts) == 3:
                    pitch = float(parts[1])
                    yaw = float(parts[2])
                    print(f"控制雲台 -> pitch: {pitch}, yaw: {yaw}")
                    cm.control_gimbal(controller, pitch=pitch, yaw=yaw)
                else:
                    print("格式錯誤: gimbal <pitch> <yaw>")

            else:
                print("未知指令")

        except Exception as e:
            print("錯誤:", e)

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

        # 2. 開啟 CMD 指令控制        
        command_line_loop(controller)
        
    except Exception as e:
        print("[main] 出現錯誤:", e)
    finally:
        controller.disconnect()
        print("連線已關閉")

if __name__ == "__main__":
    main()
