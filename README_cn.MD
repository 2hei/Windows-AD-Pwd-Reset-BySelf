使用Pytthon修改[重置]Windows AD 用户的密码

根据邮箱

# 根据Dockerfile生成build镜像，基础镜像为python3.13.0
docker build --force-rm -t winad:v0.1 .

# [可选]，使用slim工具缩减镜像大小，镜像大小从1.04G缩减到104M，10倍左右。
/data/codes/dslim-slim/dist_linux/slim build --expose 5000 --include-path /root --include-path /usr/local winad:v0.1
