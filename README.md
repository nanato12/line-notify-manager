# line-notify-manager

- Obtain information about the groups to which they are sent
- Issue personal access tokens

## Usage

### Login with QR

```python
from notify_manager import NotifyManager

manager = NotifyManager()
```

### Login with Email (Not implemented)

```python
from notify_manager import NotifyManager

manager = NotifyManager(email='xxx@xxx.com', password='XXXXXXXX')
```

### Re-login

By specifying `session_name` as an argument to `NotifyManager`, it is possible to re-login with the stored credentials.

The advantage is that you no longer need to enter a PIN code.

After the first successful login, cookies and cert information are stored in the `.sessions`.

If `session_name` is not specified, the default value `notify` is used

- Cert information
  - `.sessions/{session_name}/cert.json`
- Cookie
  - `.sessions/{session_name}/cookie.json`

```python
from notify_manager import NotifyManager

# session_name: notify
# .sessions/notify/cert.json
# .sessions/notify/cookie.json
manager = NotifyManager()

# session_name: sub
# .sessions/sub/cert.json
# .sessions/sub/cookie.json
manager = NotifyManager(session_name='sub')
```

### Obtain information about the groups to which they are sent

The `get_group_list` function can be used to obtain a list of groups to send to.

The return value of this function is [`list[Group]`](./notify_manager/models/group.py).

```python
groups = manager.get_group_list()
print(f"group count: {len(groups)}")
# 18

for g in groups:
    print(f"{g=}")
    # g=Group(mid='xxx', name='group name', pictureUrl='https://profile.line-scdn.net/xxx/preview')
```

### Issue personal access tokens

The `issue_token` function can be used to issue a personal access token.

The first argument is the name of the notify.

**If you are sending to a group**, the second argument is the [`Group`](./notify_manager/models/group.py) object to which you want to send the message.

```python
token = manager.issue_token("my notify")
print(f"[issue] {token=}")
# [issue] token='XXXXXXXXXXXXXXXXXXXX'

token = manager.issue_token("my notify", groups[0])
print(f"[issue] {token=}")
# [issue] token='XXXXXXXXXXXXXXXXXXXX'
```

## Combination with [`line-notify-sdk`](https://github.com/nanato12/line-notify-sdk)

```bash
$ pip install line-notify-sdk
```

```python
from notify import Notify

n = Notify(token=token)
r = n.send_text("hello")

print(r.json())
# {'status': 200, 'message': 'ok'}
```

## GitHub Actions

The following linter results are detected by GitHub Actions.

- ruff
- mypy
