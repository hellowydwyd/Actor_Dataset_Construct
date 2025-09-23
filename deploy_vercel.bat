@echo off
echo 🚀 开始Vercel部署...

REM 检查Node.js
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 请先安装Node.js: https://nodejs.org/
    pause
    exit /b 1
)

REM 安装Vercel CLI
echo 📦 安装Vercel CLI...
npm install -g vercel

REM 登录Vercel
echo 🔐 登录Vercel...
vercel login

REM 生成唯一项目名称
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set PROJECT_NAME=actor-face-recognition-%datetime:~0,14%

echo 📝 使用项目名称: %PROJECT_NAME%

REM 部署到生产环境
echo 🌐 部署到生产环境...
vercel --prod --name %PROJECT_NAME%

echo ✅ 部署完成！
echo 🔗 请查看Vercel控制台获取访问地址
pause
