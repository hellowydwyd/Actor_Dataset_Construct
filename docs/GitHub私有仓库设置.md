# GitHub 私有仓库设置指南

## 🔒 将现有仓库设为私有

### 方法1: 通过GitHub网页设置 (推荐)

1. **访问您的仓库**
   - 打开：https://github.com/hellowydwyd/Actor-Dataset-Construct

2. **进入设置页面**
   - 点击仓库顶部的 **"Settings"** 标签

3. **找到危险区域**
   - 滚动到页面底部
   - 找到 **"Danger Zone"** (危险区域)

4. **更改可见性**
   - 点击 **"Change repository visibility"**
   - 选择 **"Make private"**

5. **确认操作**
   - 输入仓库名称确认：`Actor-Dataset-Construct`
   - 点击 **"I understand, change repository visibility"**

### 方法2: 通过GitHub CLI (命令行)

如果您安装了GitHub CLI：
```bash
# 安装GitHub CLI (如果未安装)
# Windows: winget install GitHub.cli
# 或访问: https://cli.github.com/

# 登录GitHub
gh auth login

# 设置仓库为私有
gh repo edit --visibility private
```

## ✅ **设置完成后的效果**

设为私有后：
- 🔒 **仅您可见**: 只有您和指定的协作者可以访问
- 🚫 **搜索隐藏**: 不会出现在GitHub公开搜索中
- 👥 **协作控制**: 可以邀请特定用户协作
- 📊 **统计私密**: 提交历史和代码统计私有

## 🎯 **私有仓库的影响**

### 对Cloud Studio部署的影响

**✅ 仍然可以部署**:
- Cloud Studio可以访问您的私有仓库
- 需要授权Cloud Studio访问GitHub私有仓库

**授权步骤**:
1. 在Cloud Studio创建工作空间时
2. 选择 **"从Git仓库导入"**
3. 输入私有仓库地址
4. 系统会提示授权GitHub访问
5. 点击授权并选择允许访问私有仓库

### 协作者管理

如果需要添加协作者：

1. **进入仓库设置**
   - GitHub仓库页面 → Settings

2. **管理访问权限**
   - 左侧菜单点击 **"Manage access"**

3. **邀请协作者**
   - 点击 **"Invite a collaborator"**
   - 输入用户名或邮箱
   - 选择权限级别：
     - **Read**: 只读权限
     - **Write**: 读写权限
     - **Admin**: 管理员权限

## 🔄 **如果需要重新设为公开**

1. 进入仓库设置
2. 找到"Danger Zone"
3. 点击 **"Change repository visibility"**
4. 选择 **"Make public"**
5. 确认操作

## 💡 **私有仓库的优势**

### 🔐 **安全保护**
- 代码和配置文件私密保护
- API密钥等敏感信息不会泄露
- 防止恶意克隆和使用

### 👥 **精确控制**
- 精确控制谁可以访问代码
- 分级权限管理
- 审计跟踪所有访问

### 🚀 **专业形象**
- 企业项目通常使用私有仓库
- 更好的知识产权保护
- 避免不必要的外部关注

## ⚠️ **注意事项**

1. **免费账户限制**
   - GitHub免费账户支持无限私有仓库
   - 私有仓库的协作者数量有限制

2. **Cloud Studio访问**
   - 首次使用私有仓库需要授权
   - 确保Cloud Studio有访问私有仓库的权限

3. **分享限制**
   - 私有仓库无法直接分享给他人查看代码
   - 可以通过邀请协作者的方式分享

## 🎯 **推荐设置**

对于您的AI项目，建议设为私有，因为：
- 🔒 保护TMDB API密钥等敏感配置
- 💼 体现项目的专业性
- 🛡️ 避免恶意使用或滥用
- 👥 精确控制访问权限

**设置完成后，您的项目仍然可以正常部署到Cloud Studio并获得公网访问！**
