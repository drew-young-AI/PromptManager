#!/bin/bash

set -e  # 開啟嚴格的錯誤處理

image_name="prompt-manager"
container_name="prompt-manager"

# 檢查 BUILD_SOURCESDIRECTORY 是否已設定
if [ -n "$BUILD_SOURCESDIRECTORY" ]; then
    echo "進入 $BUILD_SOURCESDIRECTORY 目錄"
    cd "$BUILD_SOURCESDIRECTORY" || exit 1
fi

echo "Docker 映像檔"
docker images

echo "Docker 容器"
docker ps -a

# 停止並移除同名的容器（如果存在）
containerId=$(docker ps -aq -f "name=$container_name")
if [ -n "$containerId" ]; then
    docker stop "$container_name" && docker rm "$containerId"
fi

# 刪除同名的映像檔（如果存在）
imageId=$(docker images -q "$image_name")
if [ -n "$imageId" ]; then
    echo "刪除舊的映像檔: $image_name"
    docker rmi "$image_name"
fi

# 建立映像檔
docker build --no-cache -t "$image_name" .

# 執行容器
if [ -n "$BUILD_SOURCESDIRECTORY" ]; then
    docker run -p 8002:8000 -d --restart unless-stopped --name "$container_name" "$image_name:latest"
else
    docker run -p 8002:8000 -d --restart unless-stopped --name "$container_name" "$image_name:latest"
fi


