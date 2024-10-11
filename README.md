# ulcoud-uimgacc

目前，UCloud镜像加速后端API已经开发完毕，但是尚没有提供前端，所以需要通过API的形式来调用镜像加速。这个仓库提供方便的脚本，能快速使用镜像加速服务。

## 原理

对于比较大的镜像，在拉取的时候，主要耗时都在下载和解压上面。而我们这里的镜像加速主要原理就在于“预加载”。即事先将镜像下载并解压到一个共享存储设备里面，在Pod启动的时候，只需要挂载这个共享存储，就可以立马使用镜像了。这样的优化可以把容器启动速度从几十分钟降低到数十秒（针对超过10G的镜像）。

使用UCloud提供的[UFS](https://docs.ucloud.cn/ufs/README)/[UPFS](https://docs.ucloud.cn/upfs/README)，我们可以高效地实现镜像预加载。

关于在containerd启动Pod时，如何拦截原有的下载解压过程，改为挂载共享储存设备，这里涉及到对镜像底层格式的修改以及containerd snapshotter插件的应用。您可以关注[Stargz Snapshotter](https://github.com/containerd/stargz-snapshotter)项目以了解更多内容。

我们基于Stargz Snapshotter做了改造以适配了UCloud。关于镜像加速，有几个核心概念需要了解：

- 原始镜像：加速前的镜像。就是需要花费数十分钟才能拉取完毕的超大镜像。
- 目标镜像：预加载后生成的特殊镜像，只需要几十秒就能拉取完毕。**需要配合镜像加速插件使用。**
- 创建目标镜像：将原始镜像预加载到UFS，并生成目标镜像的过程。
- 镜像加速插件：一个特殊的containerd snapshotter，当判断到容器使用了目标镜像，会跳过下载解压过程，并挂载UFS读取其中的镜像数据。

下面，我们将引导您如何在UK8S中开启镜像加速，基于原始镜像生成目标镜像，最后使用目标镜像以实现镜像加速。

## 开始前的准备

您需要在UCloud控制台准备好：

- 一个UK8S集群。版本必须大于等于`1.26`。
- 一个UFS，必须跟UK8S集群在同一个VPC下面，并设置好挂载点。
- 您需要加速镜像的UHub用户名和密码（需要有推送权限）。
- 在UCloud控制台创建的API公钥和私钥。

> [!IMPORTANT]
> 在使用镜像加速的过程中，切勿更改或删除UFS，最好不要动里面的任何文件，否则可能会导致容器出现IO错误或节点NotReady！

此外，需要在您的机器上面准备好一个python3环境。

克隆本项目到您的机器上面，进入项目并准备好python环境：

```bash
git clone https://github.com/fioncat/ulcoud-uimgacc.git /path/to/ucloud-uimgacc
cd /path/to/ucloud-uimgacc
python3 -m venv ./venv
./venv/bin/pip3 install -r requirements.txt
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
./venv/bin/python3 uimgacc.py enable
```

开启之后，使用`get`命令可以查看开启状态：

```bash
./venv/bin/python3 uimgacc.py get
```

`get`命令会输出JSON，下面是一个输出实例以及对字段的解释：

```javascript
{
    "Action": "GetUK8SImageAccelerateResponse",
    "RetCode": 0,
    "Enable": true,  // 是否开启了镜像加速
    "NfsReady": true, // 镜像加速使用的UFS是否就绪
    "AgentReady": true,  // 镜像加速agent是否就绪，如果不就绪，将无法进行查看、创建、删除操作。这时请检查您的集群中`kube-system/uimgacc-agent`这个Deployment的状态。
    "Status": "Ready", // 镜像加速状态。有几种枚举值：Ready(正常)，Creating(正在创建目标镜像)，CreateError(创建失败)，Deleting(正在删除)，DeleteError(删除失败)，Unknown(未知，如果agent未就绪或是有其他异常，将会是这个状态)
    "Error": "", // 当创建或删除失败时，这里会显示错误信息
    "Images": [  // 目前已经预加载的镜像列表，在创建和删除过程中，或是agent还没有就绪时，这里会强制为空
        {
            "OriginalImage": "uhub.service.ucloud.cn/testuk8s-wenqian/bigfile:latest",  // 原始镜像
            "TargetImage": "uhub.service.ucloud.cn/testuk8s-wenqian/bigfile:latest-acc", // 目标镜像
            "Size": 16113099111, // 原始镜像大小
            "Layers": 2  // 镜像层数
        },
        {
            "OriginalImage": "uhub.service.ucloud.cn/testuk8s-wenqian/nginx:latest",
            "TargetImage": "uhub.service.ucloud.cn/testuk8s-wenqian/nginx:latest-acc",
            "Size": 138967144,
            "Layers": 5
        }
    ],
    "SubnetId": "xxxx",  // 镜像加速UFS的子网ID
    "NfsAddr": "xxxx"  // 镜像加速UFS的挂载点
}
```

当您需要对某个镜像进行加速，需要进行创建操作：

```bash
./venv/bin/python3 uimgacc.py create <original_image> <target_image>
```

一般我们建议`<target_image>`是`<original_image>`加上`-acc`后缀。

镜像加速会占据您的UFS空间，如果某个镜像不再使用了，可以进行删除操作以释放UFS空间：

```bash
./venv/bin/python3 uimgacc.py delete <original_image>
```

> [!IMPORTANT]
> 在删除前请确保没有Pod在使用目标镜像了，强行删除会导致IO错误！

当您不再需要使用镜像加速，使用下面的命令来关闭：

```bash
./venv/bin/python3 uimgacc.py disable
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
