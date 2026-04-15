#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File   : camera_command.py  
Author : FantasyWilly   
Email  : bc697522h04@gmail.com  
SPDX-License-Identifier: Apache-2.0

開發公司:
    • 先飛科技 (XF)

功能總覽:
    • 根據 [廠家手冊] 編寫 控制命令

遵循:
    • Google Python Style Guide (含區段標題)
    • PEP 8 (行寬 ≤ 88, snake_case, 2 空行區段分隔)
"""

# ------------------------------------------------------------------------------------ #
# Imports
# ------------------------------------------------------------------------------------ #
# 專案內部模組
from .gcu_controller import GCUController


# ------------------------------------------------------------------------------------ #
# 無特別指令 (command = 0x00)
# ------------------------------------------------------------------------------------ #
# -------------------------------- (empty) 空命令 ------------------------------------- #
def empty(controller: GCUController) -> None:
    print("發送 [指令] : [empty] - 空指令")
    try:
        controller.send_command(
            command=0x00,
            parameters=b'',
            enable_request=True
        )
    except Exception as e:
        print("[empty] 發送指令時出現錯誤:", e)

# -------------------------- (control_gimbal) 控制雲台角度 ----------------------------- #
def control_gimbal(controller: GCUController, pitch: float, yaw: float) -> None:
    print(f"發送 [指令] : [control_gimbal] - 控制雲台, pitch: {pitch}°, yaw: {yaw}°")
    try:
        controller.send_command(
            command=0x00,
            parameters=b'',
            enable_request=True,
            pitch=pitch,                # 傳入俯仰角參數(單位：度)
            yaw=yaw                     # 傳入偏航角參數(單位：度)
        )
    except Exception as e:
        print("[control_gimbal] 發送指令時出現錯誤:", e)


# ------------------------------------------------------------------------------------ #
# 有特別指令 (command = 0x01, 0x02...)
# ------------------------------------------------------------------------------------ #
# ------------------------------ (calibration) 校準 ----------------------------------- #
def calibration(controller: GCUController) -> None:
    print("發送 [指令] : [calibration] - 校準")
    try:
        controller.send_command(
            command=0x01,
            parameters=b'',
            enable_request=True
        )
    except Exception as e:
        print("[reset] 發送指令時出現錯誤:", e)

# --------------------------------- (reset) 回中 -------------------------------------- #
def reset(controller: GCUController) -> None:
    print("發送 [指令] : [reset] - 回中")
    try:
        controller.send_command(
            command=0x03,
            parameters=b'',
            enable_request=True
        )
    except Exception as e:
        print("[reset] 發送指令時出現錯誤:", e)

# --------------------------------- (lock) 鎖定 --------------------------------------- #
def lock(controller: GCUController) -> None:
    print("發送 [指令] : [lock] - 鎖定")
    try:
        controller.send_command(
            command=0x11,
            parameters=b'',
            enable_request=True
        )
    except Exception as e:
        print("[lock] 發送指令時出現錯誤:", e)

# -------------------------------- (follow) 跟隨 -------------------------------------- #
def follow(controller: GCUController) -> None:
    print("發送 [指令] : [follow] - 跟隨")
    try:
        controller.send_command(
            command=0x12,
            parameters=b'',
            enable_request=True
        )
    except Exception as e:
        print("[follow] 發送指令時出現錯誤:", e)

# --------------------------------- (down) 向下 --------------------------------------- #
def down(controller: GCUController) -> None:
    print("發送 [指令] : [down] - 向下")
    try:
        controller.send_command(
            command=0x13,
            parameters=b'',
            enable_request=True
        )
    except Exception as e:
        print("[down] 發送指令時出現錯誤:", e)

# ----------------------------- (track) 跟蹤模式 - [開 & 關] --------------------------- #
def track_in(controller: GCUController, x0: int, y0: int, x1: int, y1: int) -> None:
    print(f"[INFO] : [track_in] 進入跟蹤模式")
    try:
        controller.send_command(
            command=0x17,
            parameters=b'\x01\x01',
            enable_request=True,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1
        )
    except Exception as e:
        print("[track_in] 發送指令時出現錯誤:", e)

def track_out(controller: GCUController, x0: int, y0: int, x1: int, y1: int) -> None:
    print(f"[INFO] : [track_out] 退出跟蹤模式")
    try:
        controller.send_command(
            command=0x17,
            parameters=b'\x01\x00',
            enable_request=True,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1
        )
    except Exception as e:
        print("[track_out] 發送指令時出現錯誤:", e)

# ------------------------------ (point_control) 指點平移 ----------------------------- #
def point_controll(controller: GCUController, x0: int, y0: int, x1: int, y1: int) -> None:
    print(f"發送 [指令] : [point_control] - 控制畫面向")
    try:
        controller.send_command(
            command=0x1A,
            parameters=b'\x01',
            enable_request=True,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1
        )
    except Exception as e:
        print("[track_in] 發送指令時出現錯誤:", e)

# --------------------------------- (photo) 拍照 ------------------------------------- #
def photo(controller: GCUController) -> None:
    print("發送 [指令] : [photo] - 拍照")
    try:
        controller.send_command(
            command=0x20,
            parameters=b'\x01',
            enable_request=True
        )
    except Exception as e:
        print("[photo] 發送指令時出現錯誤:", e)

# --------------------------------- (video) 錄影 -------------------------------------- #
def video(controller: GCUController) -> None:
    print("發送 [指令] : [video] - 錄影")
    try:
        controller.send_command(
            command=0x21,
            parameters=b'\x01',
            enable_request=True
        )
    except Exception as e:
        print("[video] 發送指令時出現錯誤:", e)

# ------------------------------- (zoom_in) 連續放大 ---------------------------------- #
def zoom_in(controller: GCUController) -> None:
    print("發送 [指令] : [zoom_in] - 連續放大")
    try:
        controller.send_command(
            command=0x22,
            parameters=b'\x01',
            enable_request=True
        )
    except Exception as e:
        print("[zoom_in] 發送指令時出現錯誤:", e)


# ------------------------------ (zoom_out) 連續縮小 ---------------------------------- #
def zoom_out(controller: GCUController) -> None:
    print("發送 [指令] : [zoom_out] - 連續縮小")
    try:
        controller.send_command(
            command=0x23,
            parameters=b'\x01',
            enable_request=True
        )
    except Exception as e:
        print("[zoom_out] 發送指令時出現錯誤:", e)

# ----------------------------- (zoom_stop) 停止放大縮小 ------------------------------- #
def zoom_stop(controller: GCUController) -> None:
    print("發送 [指令] : [zoom_stop] - 停止放大縮小")
    try:
        controller.send_command(
            command=0x24,
            parameters=b'\x01',
            enable_request=True
        )
    except Exception as e:
        print("[zoom_stop] 發送指令時出現錯誤:", e)


# ----------------------------- (zoom_point) 指定倍率 --------------------------------- #
def zoom_set(controller: GCUController, zoom: float, cam_id: int = 1) -> None:
    print(f"發送 [指令] : [zoom_point] - 指定倍率 {zoom}x")

    try:
        # 負值區（直接倍率）
        value = int(-zoom * 10)

        zoom_bytes = value.to_bytes(2, byteorder='little', signed=True)

        # ⚠️ 一定要加 cam_id
        params = bytes([cam_id]) + zoom_bytes

        controller.send_command(
            command=0x25,
            parameters=params,
            enable_request=True
        )

    except Exception as e:
        print("[zoom_set] 發送指令時出現錯誤:", e)

# --------------------------------- (focus) 聚焦 -------------------------------------- #
def focus(controller: GCUController) -> None:
    print("發送 [指令] : [focus] - 聚焦")
    try:
        controller.send_command(
            command=0x26,
            parameters=b'\x01',
            enable_request=True
        )
    except Exception as e:
        print("[focus] 發送指令時出現錯誤:", e)

# ------------------------------ (OSD) OSD畫面 - [開 & 關] ---------------------------- #
def osd_on(controller: GCUController) -> None:
    print("發送 [指令] : [OSD - On] - OSD開啟")
    try:
        controller.send_command(
            command=0x73,
            parameters=b'\x01',
            enable_request=True
        )
    except Exception as e:
        print("[focus] 發送指令時出現錯誤:", e)

def osd_off(controller: GCUController) -> None:
    print("發送 [指令] : [OSD - Off] - OSD關閉")
    try:
        controller.send_command(
            command=0x73,
            parameters=b'\x00',
            enable_request=True
        )
    except Exception as e:
        print("[focus] 發送指令時出現錯誤:", e)

# ----------------------------- (Laser) 雷射測距 - [開 & 關] --------------------------- #
def laser_on(controller: GCUController) -> None:
    print("發送 [指令] : [Laser - On] - 測距開啟")
    try:
        controller.send_command(
            command=0x81,
            parameters=b'\x02',
            enable_request=True
        )
    except Exception as e:
        print("[focus] 發送指令時出現錯誤:", e)

def laser_off(controller: GCUController) -> None:
    print("發送 [指令] : [Laser - Off] - 測距關閉")
    try:
        controller.send_command(
            command=0x81,
            parameters=b'\x00',
            enable_request=True
        )
    except Exception as e:
        print("[focus] 發送指令時出現錯誤:", e)

# ----------------------- (digital_zoom) 數字變焦 - [開 & 關] --------------------------- #
def set_digital_zoom(controller: GCUController, enable: bool) -> None:
    print(f"[指令] 數字變焦 {'開' if enable else '關'}")

    try:
        param = b'\x01' if enable else b'\x00'

        controller.send_command(
            command=0x76,
            parameters=param,
            enable_request=True
        )
    except Exception as e:
        print("[set_digital_zoom] error:", e)