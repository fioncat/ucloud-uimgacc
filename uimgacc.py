import sys
import json
import logging

from ucloud.core import exc
from ucloud.client import Client

config = {
    "region": "cn-wlcb",  # 集群所在的地域，如cn-wlcb
    "project_id": "",  # 集群所在的项目ID，可以在控制台上查看
    "public_key": "",  # UCloud API公钥
    "private_key": "",  # UCloud API私钥
    "cluster_id": "",  # 集群ID
    "subnet_id": "",  # UFS挂载点的子网ID
    "nfs_addr": "",  # UFS挂载点IP地址，需要跟集群在同一个VPC内
    "uhub_username": "",  # UHUB用户名
    "uhub_password": "",  # UHUB密码
}

args = sys.argv[1:]

if len(args) < 1:
    print("Usage: uimgacc.py <action>")
    sys.exit(1)

action = args[0]

logger = logging.getLogger("ucloud")
logger.disabled = True

client = Client({
    "region": config["region"],
    "project_id": config["project_id"],
    "public_key": config["public_key"],
    "private_key": config["private_key"],
})

try:
    need_show_resp = False
    need_wait = False
    if action == "enable":
        print("⌛正在开启镜像加速...")
        req_action = "EnableUK8SImageAccelerate"
        req = {
            "ClusterId": config["cluster_id"],
            "NfsAddr": config["nfs_addr"],
            "SubnetId": config["subnet_id"],
            "UHubUsername": config["uhub_username"],
            "UHubPassword": config["uhub_password"],
        }
    elif action == "disable":
        print("⌛正在关闭镜像加速...")
        req_action = "DisableUK8SImageAccelerate"
        req = {
            "ClusterId": config["cluster_id"],
        }
    elif action == "create":
        if len(args) < 3:
            print("Usage: uimgacc.py create <original_image> <target_image>")
            sys.exit(1)
        original_image = args[1]
        target_image = args[2]
        print("⌛正在创建镜像加速...")
        req_action = "CreateUK8SImageAccelerate"
        req = {
            "ClusterId": config["cluster_id"],
            "OriginalImage": original_image,
            "TargetImage": target_image,
        }
        need_wait = True
    elif action == "delete":
        if len(args) < 2:
            print("Usage: uimgacc.py delete <image>")
            sys.exit(1)
        print("⌛正在删除镜像加速...")
        image = args[1]
        req_action = "DeleteUK8SImageAccelerate"
        req = {
            "ClusterId": config["cluster_id"],
            "Image": image,
        }
        need_wait = True
    elif action == "get":
        print("⌛正在获取镜像加速...")
        need_show_resp = True
        req_action = "GetUK8SImageAccelerate"
        req = {
            "ClusterId": config["cluster_id"],
        }
    else:
        print(f"❓未知操作：{action}")
        sys.exit(1)
    resp = client.invoke(req_action, req)
except exc.UCloudException as e:
    print(f"❌ 操作失败，错误信息：{e}")
    sys.exit(1)
else:
    if need_wait:
        print("⏰该操作需要等待，请持续使用get命令观察操作执行状态")
    else:
        print("✅ 操作成功")
    if need_show_resp:
        print(json.dumps(resp, indent=4))
