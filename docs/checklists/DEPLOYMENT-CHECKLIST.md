# v41.0.0 "Coverage" Production Deployment Checklist

## Completed

- [ ] Git tag v41.0.0 created and pushed
- [ ] GitHub release created with comprehensive notes
- [ ] RPM packages built (via CI auto-release pipeline)
- [ ] Release announcement drafted: `docs/releases/RELEASE-ANNOUNCEMENT.md`

---

## 1. Publish RPM to Fedora COPR

### Prerequisites

```bash
# Install COPR CLI
pkexec dnf install copr-cli

# Configure COPR credentials
# Visit: https://copr.fedorainfracloud.org/api/
# Download ~/.config/copr and save to your home directory
```

### Create COPR Project (first time only)

```bash
copr-cli create loofi-fedora-tweaks \
  --chroot fedora-43-x86_64 \
  --description "System tweaks and optimizations for Fedora Linux" \
  --instructions "pkexec dnf copr enable loofitheboss/loofi-fedora-tweaks && pkexec dnf install loofi-fedora-tweaks"
```

### Upload SRPM

```bash
# From project root
copr-cli build loofi-fedora-tweaks ~/rpmbuild/SRPMS/loofi-fedora-tweaks-41.0.0-1.src.rpm

# Monitor build progress
copr-cli watch-build <build-id>
```

### Verify COPR Installation

```bash
# On a clean Fedora system
pkexec dnf copr enable loofitheboss/loofi-fedora-tweaks
pkexec dnf install loofi-fedora-tweaks

# Test installation
loofi-fedora-tweaks --version
# Expected: 41.0.0 Coverage
```

---

## 2. Deploy Web Service to Production Server

### Server Prerequisites

- Fedora 43 or RHEL 9 server
- Domain name pointing to server IP
- Ports 80/443 open in firewall

### Step 1: Install Package

```bash
pkexec dnf copr enable loofitheboss/loofi-fedora-tweaks
pkexec dnf install loofi-fedora-tweaks nginx certbot python3-certbot-nginx

# Create service user
pkexec useradd -r -s /bin/nologin -d /opt/loofi-fedora-tweaks loofi
```

### Step 2: Install Systemd Service

```bash
pkexec cp loofi-fedora-tweaks.service /etc/systemd/system/
pkexec systemctl daemon-reload
pkexec systemctl enable loofi-fedora-tweaks
pkexec systemctl start loofi-fedora-tweaks

# Verify service
pkexec systemctl status loofi-fedora-tweaks
curl http://127.0.0.1:8000/api/health
```

### Step 3: Configure Nginx Reverse Proxy

```bash
pkexec cp loofi-nginx.conf /etc/nginx/conf.d/loofi.conf

# Edit domain name
pkexec sed -i 's/loofi.example.com/YOUR_DOMAIN/g' /etc/nginx/conf.d/loofi.conf

# Test nginx config
pkexec nginx -t
```

### Step 4: Obtain Let's Encrypt Certificate

```bash
pkexec certbot certonly --standalone -d YOUR_DOMAIN --email your@email.com --agree-tos
pkexec systemctl start nginx
pkexec systemctl enable nginx
pkexec systemctl enable certbot-renew.timer
```

### Step 5: Verify Production Deployment

```bash
# Test HTTPS endpoint
curl https://YOUR_DOMAIN/api/health
# Expected: {"status": "ok", "version": "41.0.0", "codename": "Coverage"}

# Test authentication flow
curl -X POST https://YOUR_DOMAIN/api/key
curl -X POST https://YOUR_DOMAIN/api/token -d "api_key=loofi_..."
curl https://YOUR_DOMAIN/api/info -H "Authorization: Bearer YOUR_TOKEN"
```

### Step 6: Firewall Configuration

```bash
pkexec firewall-cmd --permanent --add-service=http
pkexec firewall-cmd --permanent --add-service=https
pkexec firewall-cmd --reload
```

---

## 3. Announce Release

### Fedora Discussion

- **Forum**: https://discussion.fedoraproject.org/c/desktop/gnome/19
- **Title**: "Loofi Fedora Tweaks v41.0.0 'Coverage' - 80% Test Coverage Milestone"
- **Content**: Use `docs/releases/RELEASE-ANNOUNCEMENT.md`

### Reddit

- **Subreddit**: r/Fedora
- **Title**: "Loofi Fedora Tweaks v41.0.0 'Coverage' - 80% Test Coverage"
- **Flair**: "New Release"

### GitHub

- [ ] Publish: https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v41.0.0

---

## 4. Post-Deployment Verification

### COPR Checklist

- [ ] COPR build succeeds for Fedora 43
- [ ] Package installs cleanly on fresh Fedora 43
- [ ] `loofi-fedora-tweaks --version` shows 41.0.0
- [ ] GUI launches successfully
- [ ] Web mode starts without errors

### Web Service Checklist

- [ ] Systemd service is active and enabled
- [ ] HTTPS certificate is valid
- [ ] `/api/health` returns 200 OK
- [ ] Authentication flow works
- [ ] Logs are clean

### Security Checklist

- [ ] API keys are stored securely (bcrypt hashed)
- [ ] JWT tokens expire correctly
- [ ] Rate limiting works on /api/token
- [ ] HTTPS redirects work
- [ ] Security headers present

---

## Rollback Plan

### If COPR Build Fails

```bash
rpmbuild -bs loofi-fedora-tweaks.spec
copr-cli build loofi-fedora-tweaks ~/rpmbuild/SRPMS/loofi-fedora-tweaks-41.0.0-1.src.rpm
```

### If Web Service Fails

```bash
pkexec systemctl stop loofi-fedora-tweaks
journalctl -u loofi-fedora-tweaks -n 100
pkexec dnf downgrade loofi-fedora-tweaks
pkexec systemctl start loofi-fedora-tweaks
```

### Emergency Contact

- **GitHub Issues**: https://github.com/loofitheboss/loofi-fedora-tweaks/issues
- **Maintainer**: @loofitheboss

---

## Success Criteria

Production deployment is complete when:

1. Package is available via `dnf install` from COPR
2. Web service is running with HTTPS on production server
3. Release announcement is posted
4. All verification tests pass
5. Monitoring is in place
