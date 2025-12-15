# MoodMend Production Checklist

Use this checklist before deploying to production.

## Pre-Deployment

### Code & Configuration
- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] `.env` file configured for production
- [ ] `DEBUG=False` in production environment
- [ ] `SECRET_KEY` changed from default
- [ ] Database path configured correctly
- [ ] CORS origins restricted to your domain

### Security
- [ ] SSL/HTTPS certificate installed
- [ ] Firewall configured (only ports 80, 443, 22 open)
- [ ] Strong passwords for all accounts
- [ ] Database file permissions restricted (chmod 600)
- [ ] Sensitive data not in version control
- [ ] API rate limiting considered
- [ ] Input validation tested

### Database
- [ ] Database initialized with correct schema
- [ ] Test data removed (if any)
- [ ] Database backup script tested
- [ ] Automated backup cron job configured
- [ ] Restore procedure tested

### Documentation
- [ ] README.md updated
- [ ] API documentation complete
- [ ] Deployment guide reviewed
- [ ] Privacy policy added
- [ ] Terms of service added

## Deployment

### Infrastructure
- [ ] Server provisioned and accessible
- [ ] Domain name configured and pointing to server
- [ ] DNS records propagated
- [ ] SSL certificate installed and auto-renewal configured
- [ ] Web server (Nginx/Apache) configured
- [ ] Application server running (systemd service)

### Application
- [ ] Dependencies installed
- [ ] Environment variables set
- [ ] Database migrated/initialized
- [ ] Static files served correctly
- [ ] API endpoints accessible
- [ ] Frontend loads correctly

### Monitoring
- [ ] Health check endpoint working (`/health`)
- [ ] Logging configured and working
- [ ] Error tracking set up (optional: Sentry)
- [ ] Uptime monitoring configured (optional)
- [ ] Analytics installed (optional: Google Analytics)

## Post-Deployment

### Testing
- [ ] Smoke tests passed
  - [ ] Homepage loads
  - [ ] User can register
  - [ ] User can login
  - [ ] Emotion analysis works
  - [ ] Logs can be created
  - [ ] Logs can be viewed
  - [ ] Charts display correctly
- [ ] Cross-browser testing (Chrome, Firefox, Safari)
- [ ] Mobile responsiveness tested
- [ ] API endpoints tested with production data

### Performance
- [ ] Page load time < 3 seconds
- [ ] API response time < 500ms
- [ ] Database queries optimized
- [ ] No console errors in browser
- [ ] No server errors in logs

### Backup & Recovery
- [ ] Initial backup created
- [ ] Backup script running automatically
- [ ] Restore procedure documented
- [ ] Disaster recovery plan in place

### Communication
- [ ] Team notified of deployment
- [ ] Users notified (if applicable)
- [ ] Support channels ready
- [ ] Rollback plan prepared

## Monitoring (First 24 Hours)

- [ ] Check error logs every 2 hours
- [ ] Monitor server resources (CPU, memory, disk)
- [ ] Track user registrations
- [ ] Monitor API response times
- [ ] Check database size growth
- [ ] Verify backups are being created

## Week 1 Tasks

- [ ] Review all error logs
- [ ] Analyze user feedback
- [ ] Check backup integrity
- [ ] Monitor server performance
- [ ] Review security logs
- [ ] Plan first update/hotfix if needed

## Ongoing Maintenance

### Daily
- [ ] Check error logs
- [ ] Monitor uptime
- [ ] Review user feedback

### Weekly
- [ ] Review analytics
- [ ] Check backup status
- [ ] Update dependencies (if needed)
- [ ] Review performance metrics

### Monthly
- [ ] Security audit
- [ ] Database vacuum/optimization
- [ ] Review and rotate logs
- [ ] Update documentation
- [ ] Plan feature updates

---

## Emergency Contacts

- **Server Provider**: [Contact info]
- **Domain Registrar**: [Contact info]
- **SSL Provider**: [Contact info]
- **On-Call Developer**: [Contact info]

---

## Rollback Procedure

If deployment fails:

1. **Stop the new version**
   ```bash
   systemctl stop moodmend
   ```

2. **Restore previous code**
   ```bash
   git checkout previous-tag
   ```

3. **Restore database** (if schema changed)
   ```bash
   python scripts/restore_database.py
   ```

4. **Restart service**
   ```bash
   systemctl start moodmend
   ```

5. **Verify rollback**
   ```bash
   curl http://localhost:3000/health
   ```

---

## Success Criteria

Deployment is successful when:
- ✅ All smoke tests pass
- ✅ No critical errors in logs
- ✅ Health check returns 200 OK
- ✅ Users can complete full workflow
- ✅ Response times within acceptable range
- ✅ Backups are being created
- ✅ Monitoring is active

---

**Deployment Date**: _______________  
**Deployed By**: _______________  
**Version**: _______________  
**Notes**: _______________
