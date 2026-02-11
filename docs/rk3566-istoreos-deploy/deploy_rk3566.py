#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RK3566-iStoreOS自动化部署脚本
实现SSH免密连接和容器自动化部署
"""

import pandas as pd
import paramiko
import time
import os
from pathlib import Path
import sys

class RK3566Deployer:
    def __init__(self, password_file):
        """
        初始化部署器
        
        Args:
            password_file (str): 密码文件路径
        """
        self.password_file = Path(password_file)
        self.ssh_client = None
        self.credentials = {}
        self.target_host = None
        
    def read_password_file(self):
        """读取密码文件获取SSH认证信息"""
        try:
            # 读取Excel文件
            df = pd.read_excel(self.password_file)
            print(f"✅ 成功读取密码文件: {self.password_file}")
            print(f"📄 文件包含 {len(df)} 行数据")
            
            # 获取第一行数据作为连接信息
            first_row = df.iloc[0]
            self.target_host = str(first_row['IP地址']).strip()
            self.credentials = {
                'username': str(first_row['用户名']).strip(),
                'password': str(first_row['密码']).strip(),
                'port': int(first_row['SSH端口']) if not pd.isna(first_row['SSH端口']) else 22,
                'remark': str(first_row['备注']).strip() if not pd.isna(first_row['备注']) else ''
            }
            
            print(f"🔐 获取认证信息:")
            print(f"   主机IP: {self.target_host}")
            print(f"   用户名: {self.credentials['username']}")
            print(f"   端口: {self.credentials['port']}")
            print(f"   备注: {self.credentials['remark']}")
            
            return True
            
        except Exception as e:
            print(f"❌ 读取密码文件失败: {e}")
            return False
    
    def establish_ssh_connection(self, retry_count=5):
        """
        建立SSH连接
        
        Args:
            retry_count (int): 重试次数
            
        Returns:
            bool: 连接是否成功
        """
        for attempt in range(retry_count):
            try:
                print(f"📡 尝试连接到 {self.target_host} (第{attempt + 1}次尝试)...")
                
                # 创建SSH客户端
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # 设置连接参数
                self.ssh_client.connect(
                    hostname=self.target_host,
                    port=self.credentials['port'],
                    username=self.credentials['username'],
                    password=self.credentials['password'],
                    timeout=60,  # 增加超时时间
                    look_for_keys=False,
                    allow_agent=False
                )
                
                print(f"✅ SSH连接成功建立!")
                
                # 测试连接
                stdin, stdout, stderr = self.ssh_client.exec_command('uname -a', timeout=30)
                result = stdout.read().decode().strip()
                print(f"🐧 远程系统信息: {result}")
                
                return True
                
            except Exception as e:
                print(f"❌ 连接失败 (尝试 {attempt + 1}/{retry_count}): {e}")
                if self.ssh_client:
                    self.ssh_client.close()
                    self.ssh_client = None
                
                if attempt < retry_count - 1:
                    wait_time = min(10 * (attempt + 1), 30)  # 递增等待时间，最大30秒
                    print(f"⏳ 等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    print("💥 所有连接尝试均失败")
                    return False
        
        return False
    
    def execute_remote_command(self, command, show_output=True):
        """
        执行远程命令
        
        Args:
            command (str): 要执行的命令
            show_output (bool): 是否显示输出
            
        Returns:
            tuple: (stdout, stderr, exit_code)
        """
        if not self.ssh_client:
            print("❌ SSH连接未建立")
            return None, None, -1
            
        try:
            if show_output:
                print(f"🔧 执行命令: {command}")
            
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            
            # 获取结果
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()
            
            if show_output:
                if output.strip():
                    print(f"📋 输出:\n{output}")
                if error.strip():
                    print(f"⚠️  错误:\n{error}")
                if exit_code != 0:
                    print(f"🚨 命令执行失败 (退出码: {exit_code})")
            
            return output, error, exit_code
            
        except Exception as e:
            print(f"❌ 执行命令失败: {e}")
            return None, str(e), -1
    
    def transfer_files(self, local_files, remote_dir):
        """
        传输文件到远程主机
        
        Args:
            local_files (list): 本地文件路径列表
            remote_dir (str): 远程目录路径
        """
        try:
            # 创建SFTP客户端
            sftp = self.ssh_client.open_sftp()
            
            # 创建远程目录
            self.execute_remote_command(f"mkdir -p {remote_dir}")
            
            print(f"📤 传输文件到 {remote_dir}:")
            
            for local_file in local_files:
                if os.path.exists(local_file):
                    filename = os.path.basename(local_file)
                    remote_path = f"{remote_dir}/{filename}"
                    
                    print(f"   传输 {filename}...")
                    sftp.put(local_file, remote_path)
                    print(f"   ✅ {filename} 传输完成")
                else:
                    print(f"   ⚠️  本地文件不存在: {local_file}")
            
            sftp.close()
            return True
            
        except Exception as e:
            print(f"❌ 文件传输失败: {e}")
            return False
    
    def deploy_deeptutor(self, work_dir="/mnt/sata1-1/docker/mycontainers/fork-DeepTutor"):
        """
        部署DeepTutor容器
        
        Args:
            work_dir (str): 工作目录路径
        """
        print(f"🚀 开始部署DeepTutor到 {work_dir}")
        
        # 1. 创建工作目录
        print("📁 创建工作目录...")
        self.execute_remote_command(f"mkdir -p {work_dir}")
        
        # 2. 检查Docker环境
        print("🐳 检查Docker环境...")
        output, error, code = self.execute_remote_command("docker --version")
        if code != 0:
            print("❌ Docker未安装或不可用")
            return False
        
        # 3. 检查存储空间
        print("💾 检查存储空间...")
        self.execute_remote_command("df -h")
        
        # 4. 配置Docker代理（使用提供的代理服务器）
        print("🌐 配置Docker代理...")
        proxy_configs = [
            "http://192.168.123.51:7892",
            "http://localhost:7892", 
            "http://192.168.123.222:7890"
        ]
        
        # 尝试配置代理
        for proxy in proxy_configs:
            print(f"   尝试代理: {proxy}")
            # 配置Docker daemon代理
            daemon_config = f'''{{
  "proxies": {{
    "default": {{
      "httpProxy": "{proxy}",
      "httpsProxy": "{proxy}"
    }}
  }}
}}'''
            
            self.execute_remote_command(f'echo \'{daemon_config}\' > /etc/docker/daemon.json')
            # 重启Docker服务
            restart_result = self.execute_remote_command("systemctl restart docker", show_output=False)
            if restart_result[2] == 0:  # 重启成功
                print(f"   ✅ Docker代理配置成功: {proxy}")
                break
            else:
                print(f"   ⚠️  代理配置失败: {proxy}")
        
        # 5. 传输本地配置文件
        print("📂 传输本地配置文件...")
        local_config_files = [
            "docker-compose-prebuilt.yml",
            ".env"
        ]
        
        if self.transfer_files(local_config_files, work_dir):
            # 重命名docker-compose文件
            self.execute_remote_command(f"cd {work_dir} && mv docker-compose-prebuilt.yml docker-compose.yml")
            print("✅ 配置文件传输完成")
        
        # 6. 创建数据目录结构
        print("🏗️  创建目录结构...")
        dirs_to_create = [
            f"{work_dir}/data",
            f"{work_dir}/config",
            f"{work_dir}/data/knowledge_bases",
            f"{work_dir}/data/user"
        ]
        
        for directory in dirs_to_create:
            self.execute_remote_command(f"mkdir -p {directory}")
        
        # 7. 拉取镜像
        print("📥 拉取DeepTutor镜像...")
        self.execute_remote_command("docker pull ghcr.io/hkuds/deeptutor:latest", show_output=False)
        
        # 8. 启动容器
        print("🏁 启动容器服务...")
        self.execute_remote_command(f"cd {work_dir} && docker-compose up -d")
        
        # 9. 验证服务状态
        print("🔍 验证服务状态...")
        time.sleep(15)  # 等待服务启动
        self.execute_remote_command("docker-compose ps")
        self.execute_remote_command("docker ps")
        
        print("🎉 DeepTutor部署完成!")
        return True
    
    def close_connection(self):
        """关闭SSH连接"""
        if self.ssh_client:
            self.ssh_client.close()
            print("🔒 SSH连接已关闭")

def main():
    """主函数"""
    # 配置参数
    password_file = "docs/docs/rk3566-istoreos-deploy/password.xls"
    work_dir = "/mnt/sata1-1/docker/mycontainers/fork-DeepTutor"
    
    print("=" * 50)
    print("🚀 RK3566-iStoreOS DeepTutor自动化部署")
    print("=" * 50)
    
    # 创建部署器实例
    deployer = RK3566Deployer(password_file)
    
    try:
        # 读取密码文件
        if not deployer.read_password_file():
            return False
        
        # 建立SSH连接
        if not deployer.establish_ssh_connection():
            return False
        
        # 执行部署
        success = deployer.deploy_deeptutor(work_dir)
        
        if success:
            print("\n" + "=" * 50)
            print("✅ 部署成功!")
            print(f"🌐 访问地址:")
            print(f"   前端界面: http://{deployer.target_host}:3782")
            print(f"   API文档: http://{deployer.target_host}:8001/docs")
            print("=" * 50)
        
        return success
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断部署")
        return False
    except Exception as e:
        print(f"\n❌ 部署过程中发生错误: {e}")
        return False
    finally:
        # 关闭连接
        deployer.close_connection()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)