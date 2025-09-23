#!/usr/bin/env python3
"""
阿里云服务器多项目部署方案
IP: 114.215.208.180
域名: 灵织.cn
"""
import subprocess
import socket
import json
from pathlib import Path

def check_used_ports():
    """检查已使用的端口"""
    print("🔍 检查服务器已使用端口...")
    
    try:
        # 检查常用端口占用
        common_ports = [80, 443, 3000, 5000, 8000, 8080, 8888, 9000]
        used_ports = []
        available_ports = []
        
        for port in common_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                used_ports.append(port)
                print(f"  🔴 端口 {port}: 已占用")
            else:
                available_ports.append(port)
                print(f"  🟢 端口 {port}: 可用")
        
        return used_ports, available_ports
        
    except Exception as e:
        print(f"  ❌ 端口检查失败: {e}")
        return [], [5001, 5002, 5003]  # 默认推荐端口

def suggest_deployment_port(available_ports):
    """建议部署端口"""
    print(f"\n🎯 端口分配建议:")
    
    # 根据可用端口推荐
    if 5000 in available_ports:
        recommended_port = 5000
        print(f"  ✅ 推荐端口: {recommended_port} (标准Flask端口)")
    elif 8080 in available_ports:
        recommended_port = 8080
        print(f"  ✅ 推荐端口: {recommended_port} (备用Web端口)")
    else:
        recommended_port = 5001
        print(f"  ✅ 推荐端口: {recommended_port} (自定义端口)")
    
    print(f"  🌐 访问地址: http://114.215.208.180:{recommended_port}")
    print(f"  🌐 域名访问: http://灵织.cn:{recommended_port}")
    
    return recommended_port

def create_nginx_config(port):
    """创建Nginx反向代理配置"""
    print(f"\n⚙️  创建Nginx反向代理配置...")
    
    nginx_config = f"""
# 人脸识别系统 Nginx配置
# 文件位置: /etc/nginx/sites-available/actor-recognition

server {{
    listen 80;
    server_name 灵织.cn 114.215.208.180;
    
    # 主站点（可能是您现有的项目）
    location / {{
        proxy_pass http://127.0.0.1:3000;  # 假设现有项目在3000端口
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    # 人脸识别系统子路径
    location /actor/ {{
        proxy_pass http://127.0.0.1:{port}/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 处理大文件上传
        client_max_body_size 100M;
        proxy_request_buffering off;
    }}
    
    # API接口
    location /actor/api/ {{
        proxy_pass http://127.0.0.1:{port}/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}

# HTTPS配置（如果有SSL证书）
server {{
    listen 443 ssl;
    server_name 灵织.cn;
    
    # SSL证书配置
    # ssl_certificate /path/to/your/cert.pem;
    # ssl_certificate_key /path/to/your/key.pem;
    
    location / {{
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    location /actor/ {{
        proxy_pass http://127.0.0.1:{port}/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 100M;
    }}
}}
"""
    
    config_file = Path('nginx_actor_recognition.conf')
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(nginx_config)
    
    print(f"  ✅ Nginx配置已创建: {config_file}")
    
    return config_file

def create_systemd_service(port):
    """创建systemd服务配置"""
    print(f"\n🔧 创建systemd服务配置...")
    
    service_config = f"""[Unit]
Description=Actor Face Recognition System
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/Actor_Dataset_Construct
ExecStart=/opt/Actor_Dataset_Construct/venv/bin/python main.py web --host 127.0.0.1 --port {port}
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

# 环境变量
Environment=FLASK_ENV=production
Environment=PYTHONPATH=/opt/Actor_Dataset_Construct

# 资源限制
MemoryLimit=1.5G
CPUQuota=150%

[Install]
WantedBy=multi-user.target
"""
    
    service_file = Path('actor-recognition.service')
    with open(service_file, 'w', encoding='utf-8') as f:
        f.write(service_config)
    
    print(f"  ✅ 系统服务配置已创建: {service_file}")
    return service_file

def create_deployment_guide():
    """创建完整的部署指南"""
    print(f"\n📋 创建阿里云部署指南...")
    
    guide_content = f"""# 🌐 阿里云服务器部署指南

## 📊 服务器信息
- **公网IP**: 114.215.208.180
- **域名**: 灵织.cn  
- **配置**: 2核2GB
- **操作系统**: Linux (推荐Ubuntu 20.04+)

## 🚀 部署步骤

### 1. 连接服务器
```bash
ssh root@114.215.208.180
# 或使用域名
ssh root@灵织.cn
```

### 2. 准备环境
```bash
# 更新系统
sudo apt-get update && sudo apt-get upgrade -y

# 安装基础依赖
sudo apt-get install -y python3 python3-pip python3-venv git
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0  # OpenCV依赖
sudo apt-get install -y fonts-wqy-microhei fonts-wqy-zenhei  # 中文字体
```

### 3. 克隆项目
```bash
cd /opt
sudo git clone https://github.com/hellowydwyd/Actor_Dataset_Construct.git
sudo chown -R www-data:www-data Actor_Dataset_Construct
cd Actor_Dataset_Construct
```

### 4. 创建虚拟环境
```bash
sudo -u www-data python3 -m venv venv
sudo -u www-data bash -c "source venv/bin/activate && pip install -r requirements-china.txt"
```

### 5. 配置API密钥
```bash
sudo -u www-data cp config/env_example .env
sudo nano .env
# 添加: TMDB_API_KEY=486ceb284a5bba2fb9dff62fb2d2c819
```

### 6. 配置系统服务
```bash
# 复制服务文件
sudo cp actor-recognition.service /etc/systemd/system/

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable actor-recognition
sudo systemctl start actor-recognition

# 检查状态
sudo systemctl status actor-recognition
```

### 7. 配置Nginx（多项目共存）
```bash
# 安装Nginx（如果未安装）
sudo apt-get install -y nginx

# 复制配置文件
sudo cp nginx_actor_recognition.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/nginx_actor_recognition.conf /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

## 🌐 访问地址

### 直接访问
- http://114.215.208.180:5001 (直接端口访问)

### 通过域名访问
- http://灵织.cn/actor/ (通过子路径访问)
- https://灵织.cn/actor/ (如果配置了SSL)

## 🔧 运维管理

### 服务管理命令
```bash
# 查看服务状态
sudo systemctl status actor-recognition

# 重启服务
sudo systemctl restart actor-recognition

# 查看日志
sudo journalctl -u actor-recognition -f

# 监控资源使用
./monitor_server.sh
```

### 更新部署
```bash
cd /opt/Actor_Dataset_Construct
sudo -u www-data git pull
sudo systemctl restart actor-recognition
```

## 💰 资源使用预估

### 内存使用
- 系统基础: 300MB
- 现有项目: 500MB (假设)
- 人脸识别系统: 1GB
- 缓冲区: 200MB
- **总计**: ~2GB ✅

### CPU使用
- 空闲时: 5-10%
- 处理图片时: 50-80%
- 视频处理时: 80-100%

## 🛡️ 安全建议

### 防火墙配置
```bash
# 开放必要端口
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 5001
sudo ufw enable
```

### 监控和备份
```bash
# 设置定时任务监控
crontab -e
# 添加: */5 * * * * /opt/Actor_Dataset_Construct/monitor_server.sh >> /var/log/actor_monitor.log
```

## 💡 多项目共存优势

✅ **共享资源**: 共用Nginx、SSL证书
✅ **域名统一**: 通过子路径区分项目  
✅ **维护简单**: 统一的运维管理
✅ **成本节约**: 无需额外服务器
"""
    
    guide_file = Path('阿里云部署指南.md')
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print(f"  ✅ 部署指南已创建: {guide_file}")

def main():
    """主函数"""
    print("☁️  阿里云多项目部署配置")
    print("="*50)
    print(f"🌐 服务器信息:")
    print(f"   IP: 114.215.208.180")
    print(f"   域名: 灵织.cn")
    print(f"   配置: 2核2GB")
    
    # 检查端口使用情况
    used_ports, available_ports = check_used_ports()
    
    # 推荐端口
    recommended_port = suggest_deployment_port(available_ports)
    
    # 创建配置文件
    nginx_config = create_nginx_config(recommended_port)
    service_config = create_systemd_service(recommended_port)
    
    # 创建部署指南
    create_deployment_guide()
    
    print(f"\n🎉 多项目部署方案已准备完成！")
    print(f"\n📋 部署后的访问方式:")
    print(f"  • 直接访问: http://114.215.208.180:{recommended_port}")
    print(f"  • 域名访问: http://灵织.cn/actor/")
    print(f"  • HTTPS访问: https://灵织.cn/actor/ (需要SSL证书)")
    
    print(f"\n💡 与现有项目共存:")
    print(f"  • 现有项目: http://灵织.cn/ (主站)")
    print(f"  • 人脸识别: http://灵织.cn/actor/ (子站)")
    print(f"  • 完全独立运行，不会冲突")

if __name__ == '__main__':
    main()
