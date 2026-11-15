#!/usr/bin/env bash
# Guarda / recupera la carpeta data/ en la rama "data" del repositorio.
# La rama se reescribe con un único commit en cada ejecución, así el repositorio no crece.
set -euo pipefail

case "${1:-}" in
  traer)
    if git ls-remote --exit-code --heads origin data >/dev/null 2>&1; then
      git fetch -q --depth 1 origin data
      git checkout FETCH_HEAD -- data/ 2>/dev/null || true
      git reset -q
      echo "Datos recuperados: $(du -sh data | cut -f1)"
    else
      echo "Primera ejecución: todavía no hay datos guardados"
    fi
    ;;
  guardar)
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/data"
    cp data/radar.db "$tmp/data/" 2>/dev/null || true
    cd "$tmp"
    git init -q -b data
    git add data
    git -c user.name="radar-bot" -c user.email="radar-bot@users.noreply.github.com" commit -qm "datos $(date -u +%FT%TZ)"
    git push -qf "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" data
    echo "Datos guardados en la rama data"
    ;;
  *)
    echo "uso: $0 traer|guardar"; exit 1 ;;
esac
