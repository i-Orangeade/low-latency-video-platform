FROM node:24-alpine AS build

WORKDIR /app
# 第一阶段使用 Node 构建 Vue 静态资源。
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# 第二阶段只保留静态文件和 Nginx 配置，最终镜像不包含 Node 和源码依赖。
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
