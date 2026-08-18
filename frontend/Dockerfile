# ===== 前端镜像（Vue 3 + Element Plus + Vite）=====
# 阶段一：构建静态资源
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# 阶段二：Nginx 托管静态文件并代理后端 API
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
