#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File   : camera_protocol.py  
Author : FantasyWilly   
Email  : bc697522h04@gmail.com  
SPDX-License-Identifier: Apache-2.0

開發公司:
    • 先飛科技 (XF)

功能總覽: 
    • CRC 計算
    • 根據 [廠家手冊] 編寫 完整封包資訊
    • 發送空命令 (回傳當前雲台資訊)

遵循:
    • Google Python Style Guide (含區段標題)
    • PEP 8 (行寬 ≤ 88, snake_case, 2 空行區段分隔)
"""

# ------------------------------------------------------------------------------------ #
# Imports
# ------------------------------------------------------------------------------------ #
# 標準庫
import struct


# --------------------------------- 發送完整指令封包 架構 -------------------------------- #
def build_packet(
    command: int,
    parameters: bytes = None,
    enable_request: bool = None,
    pitch: float = None, yaw: float = None,
    x0: int = None, y0: int = None, x1: int = None, y1: int = None,
    width: int = None, height: int = None,
) -> bytes:
    
    """
    - 說明 [build_packet] 構建相機指令封包框架
        1. 協議頭
        2. 接收 控制命令, 控制參數等...
        3. 計算 CRC 校驗碼 

    args:
        • command (int)         - 指令代碼 (0x01, 0x20, ...)
        • parameters (bytes)    - 指令的參數 (default `None`)
        • enable_request (bool) - 是否需要啟用 GCU 返回數據 (default `True`)
        • pitch, yaw (float)    - 角度值 (default `None`)
        • x0, y0, x1, y1 (int)  - 左上 & 右下點 (default `None`)
        • width, height (int)   - 影像畫素 (default `None`)

    returns:
        • packet (bytes)        - 組好的完整封包 (包含 2 byte CRC)
    """

    # ------------------------------ Step1. 大致框架區--------------------------------- #
    # 開頭（固定 5 bytes）[0 ~ 4]
    header = b'\xA8\xE5'            # 協議頭
    length_bytes = b'\x00\x00'      # 包長度占位符（後續填充實際值）
    version = b'\x02'               # 協議版本

    # 主幀（固定 32 bytes）[5 ~ 36]
    if enable_request:
        main_frame  = bytearray(b'\x00' * 32)
        main_frame[25] = 0x01
    else:
        main_frame  = bytearray(b'\x00' * 32)

    # 副幀（固定 32 bytes）[37 ~ 68]
    sub_frame   = bytearray(b'\x00' * 32)

    # 控制命令（浮動 bytes）[69 ~ 未知]
    command_to_bytes = command.to_bytes(1, 'little')
    if parameters is None:
        parameters = b''

    # A. 初步封裝 [大致框架]
    payload = bytearray(
        header + 
        length_bytes + 
        version + 
        main_frame + 
        sub_frame
    )

    # --------------------------- Step2. 特殊指令編寫區 -------------------------------- #
    # 無指令(0x00) → 角度控制：roll(5–7)、yaw(7–9)、pitch(9–11)、結尾標誌 0x04
    if command == 0x00 and (pitch is not None or yaw is not None):
        pitch_value = int(pitch * 100)
        yaw_value = int(yaw * 100)

        # little-endian 2 字節
        payload[5:7]    = struct.pack('<h', 0)    # roll 保留 0
        payload[7:9]    = struct.pack('<h', pitch_value)
        payload[9:11]   = struct.pack('<h', yaw_value)
        payload[11]     = 0x04

    # 指令 (0x17) 追蹤模式, (0x1A) 指點平移
    valid_params = None
    if command == 0x17:
        valid_params = (b'\x01\x01', b'\x01\x00')
    elif command == 0x1A:
        valid_params = (b'\x01',)

    if valid_params and parameters in valid_params and None not in (x0, y0, x1, y1):

        # 解析率轉換 (左上[0,0], 右下[10000,10000])
        x0 = int(x0 / width  * 10000)
        y0 = int(y0 / height * 10000)
        x1 = int(x1 / width  * 10000)
        y1 = int(y1 / height * 10000)

        # 將四個坐標統一轉為整數列表
        coords = [int(x0), int(y0), int(x1), int(y1)]
        
        # 為每個整數生成 2 字節小端表示, 並保存到列表
        byte_chunks = []
        for c in coords:
            byte_chunks.append(c.to_bytes(2, byteorder='little'))
        
        # 把原本的 parameters 與所有坐標的 bytes 連接起來
        parameters = parameters + b''.join(byte_chunks)

    # B. 二次封裝 [大致框架] + [指令控制]
    payload += command_to_bytes + parameters

    # ---------------------------- Step3. 封包總長度計算 -------------------------------- #
    # 計算總長度 (加上CRC 校驗碼 +2)
    total_length = len(payload) + 2
    length_bytes = total_length.to_bytes(2, 'little')

    # C. 三次封裝 [大致框架] + [指令控制] + [修改真實長度]
    payload[2:4] = length_bytes

    # ---------------------------- Step4. 最終效驗碼計算 -------------------------------- #
    # 計算 CRC 校驗碼
    crc_value = calculate_crc(payload)
    crc_bytes = crc_value.to_bytes(2, 'big')

    # D. 最終封裝 [大致框架] + [指令控制] + [修改真實長度] + [CRC效驗碼]
    payload += crc_bytes

    return bytes(payload)

# ----------------------------------- 計算 CRC 校驗碼 ---------------------------------- #
def calculate_crc(data: bytes) -> int:
    crc = 0
    crc_table = [
        0x0000, 0x1021, 0x2042, 0x3063,
        0x4084, 0x50A5, 0x60C6, 0x70E7,
        0x8108, 0x9129, 0xA14A, 0xB16B,
        0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
    ]

    # 高4位和低4位分別進行 CRC 計算
    for byte in data:
        crc = ((crc << 4) ^ crc_table[(crc >> 12) ^ (byte >> 4)]) & 0xFFFF
        crc = ((crc << 4) ^ crc_table[(crc >> 12) ^ (byte & 0x0F)]) & 0xFFFF
    return crc
