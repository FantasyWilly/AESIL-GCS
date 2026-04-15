#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File   : camera_decoder.py
Author : FantasyWilly   
Email  : bc697522h04@gmail.com  
SPDX-License-Identifier: Apache-2.0

開發公司:
    • 先飛科技 (XF)

功能總覽: 
    • 接收 資料
    • 解碼 資料

遵循:
    • Google Python Style Guide (含區段標題)
    • PEP 8 (行寬 ≤ 88, snake_case, 2 空行區段分隔)
"""

# ------------------------------------------------------------------------------------ #
# Imports
# ------------------------------------------------------------------------------------ #
# 標準庫
import struct


# ------------------------------- GCU 返回數據解碼 ------------------------------------- #
def decode_gcu_response(response: bytes) -> dict:
    """    
    - 說明 (def) [decode_gcu_response] 解碼相機回傳數據
        1. 接收 16 進制數值
        2. 解碼 16 進制數值

    args:
        • ip (str)          - 目標主機 IP
        • port (int)        - 目標主機 Port
        • timeout (float)   - Socket 超時時間 (預設 5 秒)

    returns:
        • data              - 解析後的資訊 (roll, yaw, pitch)
    """
    
    # 初始化字典
    data = {}

    # ---------------------------- 1. 檢查協議頭是否正確 -------------------------------- #
    # 先檢查至少要有 72 bytes 或更多 (視協議長度)
    if len(response) < 72:
        data['error'] = '封包長度不足,無法解析'
        return data

    # 檢查協議頭 (是否為 0x8A 0x5E)
    header1, header2 = response[0], response[1]
    if not (header1 == 0x8A and header2 == 0x5E):
        data['error'] = f'協議頭錯誤: {header1:02X}{header2:02X}'
        return data

    # ----------------------- 2-1. 解碼相機 (roll, pitch, yaw) ------------------------ #
    # 嘗試讀取 roll/pitch/yaw (Byte18~19, 20~21, 22~23)
    roll_bytes  = response[18:20]   # 2 bytes   (絕對 - ROLL)
    pitch_bytes = response[20:22]   # 2 bytes   (絕對 - PITCH)
    yaw_bytes   = response[16:18]   # 2 bytes   (相對 - YAW)

    # 有號 16-bit (S16): struct.unpack("<h") => littel-endian 16位元有正負數
    roll_raw  = struct.unpack("<h", roll_bytes)[0]
    pitch_raw = struct.unpack("<h", pitch_bytes)[0]
    yaw_raw   = struct.unpack("<h", yaw_bytes)[0]

    # 分辨率 0.01
    rollangle  = roll_raw  * 0.01
    pitchangle = pitch_raw * 0.01
    yawangle   = yaw_raw   * 0.01

    # 添加 進 data 列表
    data['rollangle']  = rollangle
    data['pitchangle'] = pitchangle
    data['yawangle']   = yawangle

    # -------------------------- 2-2. 解碼相機 (targetdist) --------------------------- #
    # 嘗試讀取 目標測距 (Byte43~46)
    targetdist_bytes  = response[43:47]   # 4 bytes

    # 無號 32-bit (U32)：struct.unpack('<I') => little-endian 32 位元無號整數
    targetdist_raw, = struct.unpack('<I', targetdist_bytes)

    # 分辨率 0.1
    targetdist = targetdist_raw * 0.1

    # 添加 進 data 列表
    data['targetdist'] = targetdist

    # ----------------------- 2-3. 解碼相機 (相機倍率 ratio) --------------------------- #
    # 嘗試讀取 相機倍率 ratio (Byte59~60)
    zoom_bytes =response[59:61]

    # 無號 16-bit (U16): struct.unpack("<H") => littel-endian 16位元無正負數
    zoom_raw = struct.unpack("<H", zoom_bytes)[0]

    # 分辨率 0.1
    zoom = zoom_raw * 0.1

    # 添加 進 data 列表
    data['zoom'] = zoom

    # ------------------------- 3. 最終回傳 Data 資料 ---------------------------------- #
    # 回傳 data 資料
    return data
