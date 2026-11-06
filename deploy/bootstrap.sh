#!/usr/bin/env bash
# One-shot setup for a fresh Ubuntu Vultr VM. Run as root from the repo checkout at /opt/prereg:
#   PREREG_DOMAIN=64-177-53-95.sslip.io VULTR_INFERENCE_KEY=... bash deploy/bootstrap.sh
set -euo pipefail
: "${PREREG_DOMAIN:?set PREREG_DOMAIN}"
: "${VULTR_INFERENCE_KEY:?set VULTR_INFERENCE_KEY}"
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a
cd /opt/prereg

apt-get update -qq
apt-get install -y -qq docker.io curl gnupg ca-certificates caddy ufw >/dev/null

# gVisor from its apt repository (gvisor.dev), registered as the runsc Docker runtime.
curl -fsSL https://gvisor.dev/archive.key | gpg --batch --yes --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" \
  > /etc/apt/sources.list.d/gvisor.list
apt-get update -qq && apt-get install -y -qq runsc >/dev/null
runsc install
systemctl restart docker

docker build -t prereg-sandbox:1 sandbox

command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
uv sync --frozen --no-dev

if ! command -v node >/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null
  apt-get install -y -qq nodejs >/dev/null
fi
(cd web && npm ci --no-audit --no-fund && NEXT_TELEMETRY_DISABLED=1 npm run build)

umask 077
printf 'VULTR_INFERENCE_KEY=%s\n' "$VULTR_INFERENCE_KEY" > /etc/prereg.env
# Sandbox scratch (/out) lives on a size-capped tmpfs, so a run cannot fill the VM's disk.
mkdir -p /var/lib/prereg/runs
grep -q ' /var/lib/prereg/runs ' /etc/fstab || \
  echo 'tmpfs /var/lib/prereg/runs tmpfs size=192m,mode=0755 0 0' >> /etc/fstab
mountpoint -q /var/lib/prereg/runs || mount /var/lib/prereg/runs
install -m 644 deploy/prereg.service /etc/systemd/system/prereg.service
printf 'PREREG_DOMAIN=%s\n' "$PREREG_DOMAIN" > /etc/default/caddy-prereg
install -m 644 deploy/Caddyfile /etc/caddy/Caddyfile
mkdir -p /etc/systemd/system/caddy.service.d
printf '[Service]\nEnvironmentFile=/etc/default/caddy-prereg\n' > /etc/systemd/system/caddy.service.d/prereg.conf

systemctl daemon-reload
systemctl enable prereg
systemctl restart prereg  # restart, not just start, so re-running the script deploys new code
systemctl restart caddy

ufw allow OpenSSH >/dev/null && ufw allow 80,443/tcp >/dev/null && ufw --force enable >/dev/null
echo "Up: https://${PREREG_DOMAIN}"
