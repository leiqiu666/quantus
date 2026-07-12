# Gitee：`git push` 失败与 SSH 配置（问题解决记录）

本文记录在本项目中遇到的 **HTTPS 401**、**首次 SSH 主机确认**、**publickey 被拒绝** 等问题及处理步骤，便于日后复用或给不熟悉 Linux 的同事照抄命令。

---

## 一、现象与原因

### 1. HTTPS 推送报 401

**终端类似信息：**

- `Missing or invalid credentials` / `Bad status code: 401`
- `fatal: Authentication failed for 'https://gitee.com/.../xxx.git/'`

**原因：** 使用 `https://` 远程地址时，Gitee 需要有效认证；账号密码往往不可用，需使用 **私人令牌**，或改用 **SSH**。

**可选处理：**

- 在 Gitee：**设置 → 安全设置 → 私人令牌** 生成令牌，推送时密码处填令牌；或
- 改用 SSH 远程（见下文）。

将远程改为 SSH 示例：

```bash
git remote set-url origin git@gitee.com:组织或用户名/仓库名.git
```

---

### 2. 首次 SSH 连接：是否信任主机

**终端类似信息：**

```text
The authenticity of host 'gitee.com (...)' can't be established.
ED25519 key fingerprint is SHA256:...
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

**含义：** 本机第一次在 `~/.ssh/known_hosts` 里记录 Gitee 服务器公钥，SSH 请你确认当前连的是真实 Gitee。

**操作：** 确认域名是 `gitee.com`、网络环境可信后，输入 **`yes`** 回车（需完整输入 `yes`）。输入 **`no`** 会中断连接。

---

### 3. `Permission denied (publickey)`

**终端类似信息：**

```text
git@gitee.com: Permission denied (publickey).
fatal: Could not read from remote repository.
```

**含义：** Gitee **没有接受**你这边提供的任何 SSH 公钥。常见原因：

- 本机 **没有** 可用的默认密钥（例如只有 `id_rsa.pub` 却没有 `id_rsa`）；
- 密钥文件名 **不是**默认的 `id_ed25519` / `id_rsa`，且 **未**在 `~/.ssh/config` 里为 `gitee.com` 指定 `IdentityFile`；
- Gitee 网页上 **未添加** 与本机私钥对应的 **公钥**。

**可选自检命令（了解用）：**

```bash
ls -la ~/.ssh
ssh -o BatchMode=yes -T git@gitee.com
test -f ~/.ssh/id_rsa && echo "存在 id_rsa" || echo "无 id_rsa"
```

---

## 二、推荐做法：为 Gitee 单独生成密钥并配置（做法 A）

下列命令在**终端**中按需执行；路径按你本机用户家目录为准（示例为生成 dedicated 密钥 `id_ed25519_gitee`）。

### 1. 生成密钥对

```bash
ssh-keygen -t ed25519 -C "你的邮箱@example.com" -f ~/.ssh/id_ed25519_gitee
```

一路按提示操作即可（可设置密码短语，也可留空）。

### 2. 在终端查看公钥（整行复制）

```bash
cat ~/.ssh/id_ed25519_gitee.pub
```

输出为 **一行**，以 `ssh-ed25519` 开头。

### 3. 在 Gitee 网页添加公钥（浏览器）

1. 登录 [Gitee](https://gitee.com)
2. 头像 → **设置** → **SSH 公钥**
3. 粘贴整段公钥，填写标题后保存

### 4. 准备目录权限并写入 `~/.ssh/config`

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
```

若尚未为 `gitee.com` 写过配置，可 **整段复制执行一次**：

```bash
if ! grep -q 'Host gitee.com' ~/.ssh/config 2>/dev/null; then
  cat >> ~/.ssh/config << 'EOF'

Host gitee.com
  HostName gitee.com
  User git
  IdentityFile ~/.ssh/id_ed25519_gitee
  IdentitiesOnly yes
EOF
  echo "已写入 gitee.com 配置"
else
  echo "配置里已有 gitee.com，跳过写入"
fi
```

### 5. 收紧私钥与 config 权限

```bash
chmod 600 ~/.ssh/id_ed25519_gitee
chmod 600 ~/.ssh/config
```

### 6. 测试 SSH 连接

```bash
ssh -T git@gitee.com
```

首次可能出现主机信任提示，输入 **`yes`**。成功时通常会出现欢迎或认证成功类提示。

### 7. 进入仓库目录并推送

```bash
cd /你的项目路径/quantus
git push
```

若提示需设置上游分支，先查看分支名再执行（将 `main` 换成实际分支名）：

```bash
git branch
git push -u origin main
```

---

## 三、与本项目相关的远程示例

本仓库曾使用的远程形式示例：

- HTTPS：`https://gitee.com/aigear/quantus.git`
- SSH：`git@gitee.com:aigear/quantus.git`

查看当前远程：

```bash
git remote -v
```

---

## 四、简要对照

| 现象 | 处理方向 |
|------|----------|
| HTTPS 401 | 私人令牌，或改用 SSH |
| 首次连接问 yes/no | 可信环境下输入 `yes` |
| `Permission denied (publickey)` | 生成密钥、网页添加公钥、`config` 指定 `IdentityFile` |

---

*文档根据一次实际排查整理，Gitee 界面文案以官网为准。*
