#!/usr/bin/env bash
# Публикует JSON-фид обновлений для одного канала в ветку `update-feed`.
#
# Используется в CI после загрузки установщика в GitHub Releases. Фид кладётся
# в `<channel>/latest.json` ветки `update-feed`, откуда его читает приложение
# через raw.githubusercontent.com (стабильный URL на канал).
#
# Аргументы:
#   1. repo      — `owner/repo`
#   2. channel   — `dev` или `main`
#   3. version   — версия релиза (например `0.1.0-dev.42`)
#   4. tag       — тег релиза (например `dev-v0.1.0-dev.42`)
#   5. installer — путь к установщику (*.exe)
#   6. sig       — путь к файлу подписи (*.exe.sig)
#   7. token     — токен GitHub с правами contents:write
set -euo pipefail

REPO="$1"
CHANNEL="$2"
VERSION="$3"
TAG="$4"
INSTALLER="$5"
SIG="$6"
TOKEN="$7"

BRANCH="update-feed"
SIG_CONTENT=$(tr -d '\r\n' < "$SIG")
INSTALLER_NAME=$(basename "$INSTALLER")
DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${TAG}/${INSTALLER_NAME}"

tmpdir=$(mktemp -d)
git clone --quiet "https://x-access-token:${TOKEN}@github.com/${REPO}" "$tmpdir/repo"
cd "$tmpdir/repo"

# Переходим на ветку фида; если её ещё нет — создаём от текущего HEAD.
if git show-ref --verify --quiet "refs/remotes/origin/${BRANCH}"; then
  git checkout --quiet "$BRANCH"
else
  git checkout --quiet -b "$BRANCH"
fi

mkdir -p "$CHANNEL"
cat > "$CHANNEL/latest.json" <<EOF
{
  "version": "${VERSION}",
  "notes": "",
  "pub_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "platforms": {
    "windows-x86_64": {
      "signature": "${SIG_CONTENT}",
      "url": "${DOWNLOAD_URL}"
    }
  }
}
EOF

git add "$CHANNEL/latest.json"
git -c user.name="kiosk-release-bot" -c user.email="actions@github.com" \
  commit --quiet -m "Update ${CHANNEL} update feed to ${VERSION}"
git push --quiet "https://x-access-token:${TOKEN}@github.com/${REPO}" "$BRANCH:$BRANCH"

echo "Фид ${CHANNEL}/latest.json обновлён до ${VERSION}"
