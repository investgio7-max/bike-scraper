# 🔐 Добавить SSH ключ на GitHub

Выполни эти шаги один раз, и я смогу автоматически создать репозиторий на GitHub!

---

## 1️⃣ SSH Ключ уже создан

Путь: `~/.ssh/id_github.pub`

Публичный ключ:
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICb0cC6RvgTQ0LiEcdzxVQBrBUQcbgni54JySgP4aCfD investgio7@gmail.com
```

---

## 2️⃣ Добавить ключ на GitHub

1. Перейди на https://github.com/settings/ssh/new
2. **Title:** `MacBook SSH Key`
3. **Key type:** Authentication Key
4. **Key:** Скопируй весь SSH ключ выше (начинается с `ssh-ed25519`)
5. Нажми **"Add SSH key"**

---

## 3️⃣ Настроить SSH для GitHub

Добавь в `~/.ssh/config`:

```
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_github
  IdentitiesOnly yes
```

Или выполни команду:

```bash
cat >> ~/.ssh/config << 'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_github
  IdentitiesOnly yes
EOF
```

---

## 4️⃣ Тест SSH доступа

```bash
ssh -T git@github.com
```

Должно вывести:
```
Hi investgio7-max! You've successfully authenticated, but GitHub does not provide shell access.
```

---

## ✅ Готово!

После этого я смогу:
- ✅ Создать репозиторий на GitHub
- ✅ Сделать push через SSH
- ✅ Настроить Railway deployment

**Выполни эти шаги и дай мне знать!** 🚀
