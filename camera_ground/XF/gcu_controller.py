#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File   : gcu_controller.py  
Author : FantasyWilly   
Email  : bc697522h04@gmail.com  
SPDX-License-Identifier: Apache-2.0 

開發公司:
    • 先飛科技 (XF)

功能總覽:
    • 管理TCP連線
    • 發送控制命令
    • 連續發送空命令 & 解碼回傳資訊

遵循:
    • Google Python Style Guide (含區段標題)
    • PEP 8 (行寬 ≤ 88, snake_case, 2 空行區段分隔)
"""


# ------------------------------------------------------------------------------------ #
# Imports
# ------------------------------------------------------------------------------------ #
# 標準庫
import socket
import threading

# 專案內部模組
from .camera_protocol import build_packet
from .camera_decoder import decode_gcu_response


# ------------------------------------------------------------------------------------ #
# [GCUController] 用於連接 發送指令和接收響應
# ------------------------------------------------------------------------------------ #
class GCUController:
    """
    - 說明 [GCUController]
        1. 接收 IP, Port 參數
        2. 管理 TCP 連線
        3. 發送 控制命令

    args:
        • ip (str)        - 目標主機 IP
        • port (int)      - 目標主機 Port
        • width (int)     - 畫面像素 (寬)
        • height (int)    - 畫面像素 (高)
        • timeout (float) - Socket 超時時間 (default: 5s)
    """

    def __init__(
        self, 
        ip: str, 
        port: int,
        width:int,
        height:int,  
        timeout: float = 5.0
    ) -> None:

        # 接收參數
        self.ip     = ip
        self.port   = port
        self.width  = width
        self.height = height
        self.sock   = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)

        # 保護整個 send/recv 流程
        self.lock = threading.Lock()

    # ----------------------------------- 開啟 TCP連接 -------------------------------- #
    def connect(self) -> None:
        self.sock.connect((self.ip, self.port))
        print(f"已連接到 GCU: {self.ip}:{self.port}")

    # ----------------------------------- 關閉 TCP連接 -------------------------------- #
    def disconnect(self) -> None:
        self.sock.close()
        print("連接已關閉")

    # ----------------------------------- 發送 控制命令 -------------------------------- #
    def send_command(
        self, 
        command: int, 
        parameters: bytes = b'', 
        enable_request: bool = None,
        pitch: float = None, yaw: float = None,
        x0: int = None, y0: int = None, x1: int = None, y1: int = None
    ) -> bytes:
        
        """
        args:
            • command (int)         - 16 進位
            • parameters (bytes)    - 16 進位 
            • enable_request (bool) - 是否須返回 GCU 數據格式   (default: True)
            • pitch, yaw (float)    - 控制台角度               (default: None) 
            • x0, y0, x1, y1 (int)  - 框選方框四角點            (default: None)

        returns:
            • response (bytes)      - 返回 GCU 數據格式
        """

        with self.lock:

            # 1. 構建數據包並發送
            packet = build_packet(
                command,
                parameters,
                enable_request,
                pitch=pitch, yaw=yaw,
                x0=x0, y0=y0, x1=x1, y1=y1,
                width=self.width, height=self.height
            )
            # print("發送 [數據包] :", packet.hex().upper())
            self.sock.sendall(packet)

            # 2. 接收本次指令的回覆
            response = self.sock.recv(256)
            # print("接收 [返回數據] :", response.hex().upper())

        # 3. 解碼本次指令回覆
        parsed = decode_gcu_response(response)
        if 'error' in parsed:
            print("解碼失敗:", parsed['error'])
        else:
            rollangle   = parsed['rollangle']
            pitchangle  = parsed['pitchangle']
            yawangle    = parsed['yawangle']
            zoom        = parsed['zoom']
            targetdist  = parsed['targetdist']
            # print(
            #     f"接收 [解碼]:"
            #     f" roll={rollangle:.2f},"
            #     f" pitch={pitchangle:.2f},"
            #     f" yaw={yawangle:.2f},"
            #     f" ratio={zoom:.1f}"
            #     f" ratio={targetdist:.1f}"
            # )

        return response

    # ---------------------------------  不斷 發送空命令 ------------------------------- #
    def loop_send_command(
        self, 
        command: int, 
        parameters: bytes = b'', 
        enable_request: bool = True,
    ) -> bytes:
        
        with self.lock:

            # 1. 構建數據包並發送
            packet = build_packet(
                command, 
                parameters, 
                enable_request
            )
            # print("發送 [數據包] :", packet.hex().upper())
            self.sock.sendall(packet)

            # 2. 接收本次指令的回覆
            response = self.sock.recv(256)
            # print("接收 [返回數據] :", response.hex().upper())

        # 3. 解碼本次指令回覆
        parsed = decode_gcu_response(response)
        if 'error' in parsed:
            print("解碼失敗:", parsed['error'])
        else:
            rollangle   = parsed['rollangle']
            pitchangle  = parsed['pitchangle']
            yawangle    = parsed['yawangle']
            zoom        = parsed['zoom']
            targetdist  = parsed['targetdist']
            # print(
            #     f"接收 [解碼]:"
            #     f" roll={rollangle:.2f},"
            #     f" pitch={pitchangle:.2f},"
            #     f" yaw={yawangle:.2f},"
            #     f" ratio={zoom:.1f}"
            #     f" ratio={targetdist:.1f}"
            # )

        return response    
