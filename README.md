# ulcoud-uimgacc

目前，UCloud镜像加速后端API已经开发完毕，但是尚没有提供前端，所以需要通过API的形式来调用镜像加速。这个仓库提供方便的脚本，能快速使用镜像加速服务。

## 开始前的准备

您需要在UCloud控制台准备好：

- 一个UK8S集群。版本必须大于等于`1.26`。
- 一个UFS，必须跟UK8S集群在同一个VPC下面，并设置好挂载点。
- 您需要加速镜像的UHub用户名和密码。
- 在UCloud控制台创建的API公钥和私钥。

此外，需要在您的机器上面准备好一个python3环境。

克隆本项目到您的机器上面，进入项目并准备好python环境：

```bash
python -m venv ./venv
./venv/bin/pip install ucloud-sdk-python3
```

编辑[uimgacc.py](uimgacc.py)文件，在`config`那里根据情况填入您的配置：

```python
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
```

请根据实际情况填写。

## 开启镜像加速

完成上面的准备工作之后，通过下面的命令来开启镜像加速：

```bash
./venv/bin/python uimgacc.py enable
```

开启之后，使用`get`命令可以查看开启状态：

```bash
./venv/bin/python uimgacc.py get
```

当您需要对某个镜像进行加速，需要将其预加载到UFS中，执行下面的命令：

```bash
./venv/bin/python uimgacc.py create <original_image> <target_image>
```

加速过程需要一定时间来执行，在执行完`create`之后，您需要不断轮询执行`get`来查看加速是否完成，完成之后`get`命令会输出加速完毕的镜像名称。如果出现错误，`get`命令也会输出错误信息。

镜像加速会占据您的UFS空间，如果某个镜像不再使用了，可以通过`delete`命令来删除它以释放UFS：

```bash
./venv/bin/python uimgacc.py delete <original_image>
```

当您不再需要使用镜像加速，使用下面的命令来关闭：

```bash
./venv/bin/python uimgacc.py disable
```

## 使用镜像加速

上面我们通过脚本来创建和查看镜像加速，要在集群中使用，请用`<target_image>`替换掉`<original_image>`。

另外，在开启了镜像加速之后，新增的节点会被打上`node.uk8s.ucloud.cn/uimgacc: "true"`标签。请确保使用了加速镜像`<target_image>`的Pod被调度到有这个标签的节点上，您可以使用亲和性来完成：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
  namespace: default
  labels:
    app: test-pod
spec:
  containers:
  - name: test-pod
    image: <target_image>
    imagePullPolicy: Always
    command: ["sh"]
    args:
      - -c
      - "sleep 36000"
  restartPolicy: Always
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: node.uk8s.ucloud.cn/uimgacc
            operator: In
            values:
            - "true"
```

关于镜像加速有任何问题，请咨询我们的技术支持。
