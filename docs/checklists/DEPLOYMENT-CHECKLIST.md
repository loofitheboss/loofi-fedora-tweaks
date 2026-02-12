# v20.0.2 "Synapse" Production Deployment Checklist

## ✅ Completed

- [ ] Git tag v20.0.2 created and pushed
- [ ] GitHub release created with comprehensive notes
- [ ] RPM packages built (binary + source)
  - Binary: `~/rpmbuild/RPMS/noarch/loofi-fedora-tweaks-20.0.2-1.noarch.rpm`
  - Source: `~/rpmbuild/SRPMS/loofi-fedora-tweaks-20.0.2-1.src.rpm`
- [ ] Web server tested and verified
- [x] Systemd service file created: `loofi-fedora-tweaks.service`
- [x] Nginx reverse proxy config created: `loofi-nginx.conf`
- [x] Release announcement drafted: `docs/releases/RELEASE-ANNOUNCEMENT.md`

---

## 📦 1. Publish RPM to Fedora COPR

### Prerequisites
```bash
# Install COPR CLI
sudo dnf install copr-cli

# Configure COPR credentials
# Visit: https://copr.fedorainfracloud.org/api/
# Download ~/.config/copr and save to your home directory
```

### Create COPR Project (first time only)
```bash
copr-cli create loofi-fedora-tweaks \
  --chroot fedora-40-x86_64 \
  --chroot fedora-41-x86_64 \
  --description "System tweaks and optimizations for Fedora Linux" \
  --instructions "sudo dnf copr enable loofitheboss/loofi-fedora-tweaks && sudo dnf install loofi-fedora-tweaks"
```

### Upload SRPM
```bash
# From project root
copr-cli build loofi-fedora-tweaks ~/rpmbuild/SRPMS/loofi-fedora-tweaks-20.0.2-1.src.rpm

# Monitor build progress
copr-cli watch-build <build-id>
```

### Verify COPR Installation
```bash
# On a clean Fedora system
sudo dnf copr enable loofitheboss/loofi-fedora-tweaks
sudo dnf install loofi-fedora-tweaks

# Test installation
loofi-fedora-tweaks --version
# Expected: 20.0.2 Synapse
```

---

## 🌐 2. Deploy Web Service to Production Server

### Server Prerequisites
- Fedora 40/41 or RHEL 9 server
- Domain name (e.g., loofi.example.com) pointing to server IP
- Ports 80/443 open in firewall

### Step 1: Install Package
```bash
# On production server
sudo dnf copr enable loofitheboss/loofi-fedora-tweaks
sudo dnf install loofi-fedora-tweaks nginx certbot python3-certbot-nginx

# Create service user
sudo useradd -r -s /bin/nologin -d /opt/loofi-fedora-tweaks loofi
```

### Step 2: Install Systemd Service
```bash
# Copy service file to systemd
sudo cp loofi-fedora-tweaks.service /etc/systemd/system/

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable loofi-fedora-tweaks
sudo systemctl start loofi-fedora-tweaks

# Verify service is running
sudo systemctl status loofi-fedora-tweaks
curl http://127.0.0.1:8000/api/health
```

### Step 3: Configure Nginx Reverse Proxy
```bash
# Copy nginx config
sudo cp loofi-nginx.conf /etc/nginx/conf.d/loofi.conf

# Edit domain name
sudo sed -i 's/loofi.example.com/YOUR_DOMAIN/g' /etc/nginx/conf.d/loofi.conf

# Add rate limiting to main nginx config
sudo tee -a /etc/nginx/nginx.conf <<EOF
http {
    # ... existing config ...
    limit_req_zone \$binary_remote_addr zone=auth_limit:10m rate=10r/m;
}
EOF

# Test nginx config
sudo nginx -t
```

### Step 4: Obtain Let's Encrypt Certificate
```bash
# Stop nginx temporarily
sudo systemctl stop nginx

# Obtain certificate
sudo certbot certonly --standalone -d YOUR_DOMAIN --email your@email.com --agree-tos

# Start nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Auto-renewal
sudo systemctl enable certbot-renew.timer
```

### Step 5: Verify Production Deployment
```bash
# Test HTTPS endpoint
curl https://YOUR_DOMAIN/api/health
# Expected: {"status": "ok", "version": "20.0.2", "codename": "Synapse"}

# Test authentication flow
curl -X POST https://YOUR_DOMAIN/api/key
# Save the api_key

curl -X POST https://YOUR_DOMAIN/api/token -d "api_key=loofi_..."
# Save the access_token

# Test authenticated endpoint
curl https://YOUR_DOMAIN/api/info -H "Authorization: Bearer YOUR_TOKEN"
```

### Step 6: Firewall Configuration
```bash
# Open HTTP/HTTPS ports
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## 📢 3. Announce Release

### Fedora Discussion
- **Forum**: https://discussion.fedoraproject.org/c/desktop/gnome/19
- **Title**: "Loofi Fedora Tweaks v20.0.2 'Synapse' - Tab Scroller Fix & Dependency Refresh"
- **Content**: Use `docs/releases/RELEASE-ANNOUNCEMENT.md` (adapt formatting for forum)
- **Tags**: #fedora-tweaks, #system-tools, #gnome

### Reddit
- **Subreddit**: r/Fedora
- **Title**: "Loofi Fedora Tweaks v20.0.2 'Synapse' - Tab Scroller Fix & Dependency Refresh"
- **Flair**: "New Release"
- **Content**: Use `docs/releases/RELEASE-ANNOUNCEMENT.md` (Reddit markdown format)

### GitHub
- [ ] Publish: https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v20.0.2

### Social Media (Optional)
- **Twitter/X**: "🚀 Loofi Fedora Tweaks v20.0.2 'Synapse' is out! Tab scroller fix + dependency refresh. Try it now: [link] #Fedora #Linux #OpenSource"
- **Mastodon**: Similar to Twitter, post on Fosstodon or fedora.im instance

---

## 🔍 4. Post-Deployment Verification

### COPR Checklist
- [ ] COPR build succeeds for Fedora 40
- [ ] COPR build succeeds for Fedora 41
- [ ] Package installs cleanly on fresh Fedora 40
- [ ] Package installs cleanly on fresh Fedora 41
- [ ] `loofi-fedora-tweaks --version` shows 20.0.2
- [ ] GUI launches successfully
- [ ] Web mode starts without errors

### Web Service Checklist
- [ ] Systemd service is active and enabled
- [ ] HTTPS certificate is valid (check with browser)
- [ ] `/api/health` returns 200 OK
- [ ] `/api/info` returns system metrics
- [ ] Authentication flow works (key → token → execute)
- [ ] Preview mode executes without errors
- [ ] Logs are clean (no errors in journalctl)

### Security Checklist
- [ ] API keys are stored securely (bcrypt hashed)
- [ ] JWT tokens expire correctly
- [ ] Rate limiting works on /api/token
- [ ] HTTPS redirects work (HTTP → HTTPS)
- [ ] Security headers are present (HSTS, CSP, etc.)
- [ ] No sensitive data in logs

### Monitoring Setup
```bash
# Monitor service logs
sudo journalctl -u loofi-fedora-tweaks -f

# Monitor nginx access
sudo tail -f /var/log/nginx/loofi-access.log

# Check for errors
sudo tail -f /var/log/nginx/loofi-error.log
```

---

## 🚨 Rollback Plan

### If COPR Build Fails
```bash
# Fix the issue locally
# Rebuild SRPM
rpmbuild -bs loofi-fedora-tweaks.spec
# Resubmit to COPR
copr-cli build loofi-fedora-tweaks ~/rpmbuild/SRPMS/loofi-fedora-tweaks-20.0.2-1.src.rpm
```

### If Web Service Fails
```bash
# Stop the service
sudo systemctl stop loofi-fedora-tweaks

# Check logs for errors
sudo journalctl -u loofi-fedora-tweaks -n 100

# Roll back to previous version if needed
sudo dnf downgrade loofi-fedora-tweaks

# Restart service
sudo systemctl start loofi-fedora-tweaks
```

### Emergency Contact
- **GitHub Issues**: https://github.com/loofitheboss/loofi-fedora-tweaks/issues
- **Maintainer**: @loofitheboss

---

## 📝 Notes

- **COPR Credentials Required**: You need to configure `~/.config/copr` with your API token from https://copr.fedorainfracloud.org/api/
- **Production Server Required**: Web service deployment requires a server with a domain name and HTTPS certificate
- **Release Announcements**: Should be posted manually by the maintainer to ensure correct formatting and community engagement

---

## 🎉 Success Criteria

Production deployment is complete when:
1. ✅ Package is available via `dnf install` from COPR
2. ✅ Web service is running with HTTPS on production server
3. ✅ Release announcement is posted to Fedora Discussion and r/Fedora
4. ✅ All verification tests pass
5. ✅ Monitoring is in place

**Current Status**: Ready for manual COPR upload and server deployment (requires credentials/server access)
