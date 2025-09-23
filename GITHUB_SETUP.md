# GitHub 设置和推送指南

## 📋 当前状态
✅ 项目已初始化Git仓库
✅ 不必要文件已清理
✅ .gitignore已配置
✅ 代码已提交到本地仓库

## 🚀 推送到GitHub步骤

### 1. 创建GitHub仓库
1. 访问 https://github.com
2. 点击右上角 "+" → "New repository"
3. 填写仓库信息：
   - **Repository name**: `Actor-Dataset-Construct`
   - **Description**: `🎬 电影演员人脸识别数据库构建系统 - 支持从电影构建演员数据集、实时视频人脸识别标注`
   - **Visibility**: Public (推荐) 或 Private
   - ❌ **不要**勾选 "Add a README file"
   - ❌ **不要**选择 .gitignore 或 license (已经有了)

### 2. 连接远程仓库
```bash
# 添加远程仓库地址
git remote add origin https://github.com/你的用户名/Actor-Dataset-Construct.git

# 设置默认分支为main
git branch -M main
```

### 3. 推送代码
```bash
# 首次推送
git push -u origin main
```

## 🔧 如果需要配置Git身份
```bash
git config --global user.name "你的用户名"
git config --global user.email "你的邮箱@example.com"
```

## 📱 完整推送命令 (复制粘贴即可)

请替换 `YOUR_USERNAME` 为您的GitHub用户名：

```bash
# 添加远程仓库
git remote add origin https://github.com/YOUR_USERNAME/Actor-Dataset-Construct.git

# 设置分支
git branch -M main

# 推送代码
git push -u origin main
```

## 🌟 推送后的效果

推送成功后，您的GitHub仓库将包含：
- 📁 完整的项目源代码
- 📖 详细的说明文档
- ⚙️ 多种部署配置文件
- 🚀 中国国内优化配置
- 🛠️ 开发环境配置

## 🎯 下一步：部署到云平台

推送成功后，您可以立即部署到：

### 腾讯云 Cloud Studio (推荐)
1. 访问：https://cloudstudio.net/
2. 导入您的GitHub仓库
3. 选择Python环境
4. 自动部署运行

### 其他平台
- Railway: https://railway.app
- Render: https://render.com  
- Vercel: https://vercel.com

## 🔍 验证推送成功

推送后检查：
1. GitHub仓库页面显示所有文件
2. README.md正确显示
3. 文件结构完整
4. .gitignore生效（不包含data/images内容等）

## ❓ 可能的问题和解决方案

### 问题1: 推送失败 (认证)
```bash
# 解决方案：配置GitHub Token
# 1. GitHub设置 → Developer settings → Personal access tokens
# 2. 生成token
# 3. 使用token作为密码
```

### 问题2: 仓库已存在
```bash
# 解决方案：使用不同的仓库名或删除现有仓库
git remote set-url origin https://github.com/YOUR_USERNAME/新仓库名.git
```

### 问题3: 分支冲突
```bash
# 解决方案：强制推送（谨慎使用）
git push --force-with-lease origin main
```
