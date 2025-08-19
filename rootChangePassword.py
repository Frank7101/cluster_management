#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import getpass
from datetime import datetime

HOSTS_FILE = "hosts.txt"
LOG_FILE = f"root_passwd_changes{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

def read_hosts(path: str) -> list[str]:
    if not os.path.isfile(path):
        print(f"[ERROR] Hosts file not found: {path}", file=sys.stderr)
        sys.exit(1)
    hosts: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            # 允许写 root@host；最终都按 ssh host（当前用户为 root）连接
            if "@" in s:
                s = s.split("@", 1)[1]
            hosts.append(s)
    return hosts

def log(line: str):
    with open(LOG_FILE, "a", encoding="utf-8") as lf:
        lf.write(f"{datetime.now():%F %T} {line}\n")

def change_local_root_password(new_pass: str) -> bool:
    """在本机修改 root 密码"""
    try:
        proc = subprocess.run(
            ["chpasswd"],
            input=f"root:{new_pass}\n",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return proc.returncode == 0
    except Exception as e:
        print(f"[ERROR] local -> {e}", file=sys.stderr)
        log(f"[ERROR] local -> {e}")
        return False

def main():
    if os.geteuid() != 0:
        print("[ERROR] 请用 root 账号在管理节点运行该脚本。", file=sys.stderr)
        sys.exit(1)

    hosts = read_hosts(HOSTS_FILE)
    print(f"日志文件: {LOG_FILE}")

    # 读取新密码（确认两次，不回显）
    p1 = getpass.getpass("请输入新的 root 密码: ")
    p2 = getpass.getpass("请再次输入新的 root 密码: ")
    if p1 != p2:
        print("[ERROR] 两次输入不一致。", file=sys.stderr)
        sys.exit(1)
    new_pass = p1
    del p1, p2

    ok = fail = 0

    # 先修改本机 root 密码
    if change_local_root_password(new_pass):
        print("[OK] localhost")
        log("[OK] localhost")
        ok += 1
    else:
        print("[FAIL] localhost", file=sys.stderr)
        log("[FAIL] localhost")
        fail += 1

    # 再修改远程节点 root 密码
    for host in hosts:
        cmd = ["ssh", host, "chpasswd"]
        try:
            proc = subprocess.run(
                cmd,
                input=f"root:{new_pass}\n",
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if proc.returncode == 0:
                print(f"[OK] {host}")
                log(f"[OK] {host}")
                ok += 1
            else:
                err = (proc.stderr or "unknown error").strip()
                print(f"[FAIL] {host} -> {err}", file=sys.stderr)
                log(f"[FAIL] {host} -> {err}")
                fail += 1
        except Exception as e:
            print(f"[ERROR] {host} -> {e}", file=sys.stderr)
            log(f"[ERROR] {host} -> {e}")
            fail += 1

    print(f"完成：成功 {ok} 台，失败 {fail} 台。详情见 {LOG_FILE}")
    sys.exit(0 if fail == 0 else 2)

if __name__ == "__main__":
    main()
