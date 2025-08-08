# Security Documentation

## Overview

This Django application implements a secure passkey (WebAuthn) and magic link authentication system with comprehensive security controls to protect against common web vulnerabilities and attacks.

## Security Features

### Authentication Security

#### Passkey Authentication (WebAuthn)
- **FIDO2/WebAuthn Standard**: Implements the latest WebAuthn specification for passwordless authentication
- **CSRF Protection**: All passkey endpoints require valid CSRF tokens
- **Session Management**: Secure session handling with sliding expiration
- **Account Lockout**: Protection against brute force attacks

#### Magic Link Authentication
- **HTTPS Enforcement**: All magic links use HTTPS in production
- **Token Security**: Custom token generator with 15-minute expiration
- **Rate Limiting**: 5 requests per user, 10 per IP per hour
- **Secure Email**: Domain-based email sending with security warnings

### Input Validation and Sanitization

#### Comprehensive Validation
- **Username Validation**: Pattern matching, reserved name blocking, length limits
- **Email Validation**: RFC-compliant email format validation
- **URL Validation**: Secure URL parsing with protocol restrictions
- **XSS Prevention**: Input sanitization removes dangerous patterns

#### Redirect Security
- **Whitelist Validation**: Only approved URLs allowed for redirects
- **Open Redirect Prevention**: Strict validation prevents malicious redirects
- **Relative Path Support**: Safe handling of relative redirect URLs

### Infrastructure Security

#### Security Headers
- **Content Security Policy (CSP)**: Prevents XSS and injection attacks
- **X-Frame-Options**: Protects against clickjacking (DENY)
- **X-Content-Type-Options**: Prevents MIME sniffing (nosniff)
- **Referrer-Policy**: Controls referrer information leakage
- **Permissions-Policy**: Disables dangerous browser features

#### CORS Configuration
- **WebAuthn-Specific**: CORS headers only on passkey endpoints
- **Origin Validation**: Only authorized domains can access endpoints
- **Preflight Support**: Proper handling of OPTIONS requests
- **Development Mode**: Localhost allowed in DEBUG mode

#### Account Lockout
- **User-Based Lockout**: 5 failed attempts trigger 15-minute lockout
- **IP-Based Lockout**: 15 failed attempts from same IP
- **Sliding Windows**: 5-minute windows for counting attempts
- **Automatic Expiration**: Lockouts expire automatically

### Session Security

#### Secure Configuration
- **Session Timeout**: 1-hour sessions with sliding expiration
- **Secure Cookies**: HttpOnly, Secure, SameSite=Lax flags
- **CSRF Protection**: Secure CSRF cookie configuration
- **Automatic Cleanup**: Expired sessions cleaned automatically

#### Passkey Sessions
- **Custom Middleware**: Specialized handling for passkey authentication
- **Session Flags**: Separate tracking for passkey vs magic link auth
- **Sliding Expiration**: 30-minute passkey session timeout

### Error Handling and Logging

#### Secure Error Responses
- **Generic Messages**: No technical details exposed to users
- **Detailed Logging**: Comprehensive server-side error logging
- **Sensitive Data Protection**: Sanitization of logs to prevent data leakage
- **Security Events**: Dedicated logging for security-related events

#### Monitoring
- **Authentication Attempts**: Logging of all login attempts
- **Magic Link Usage**: Tracking of magic link requests and verification
- **Account Lockouts**: Monitoring of lockout events
- **Security Violations**: Logging of potential attacks

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///db.sqlite3

# Security
SECRET_KEY=your-secret-key-here
DEBUG=False

# Email Configuration
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Magic Link Security
MAGIC_LINK_FORCE_HTTPS=True
MAGIC_LINK_TIMEOUT=900
MAGIC_LINK_RATE_LIMIT_PER_USER=5
MAGIC_LINK_RATE_LIMIT_PER_IP=10

# Account Lockout
ACCOUNT_LOCKOUT_MAX_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION=900
ACCOUNT_LOCKOUT_ATTEMPT_WINDOW=300
```

### Django Settings

#### Security Settings
```python
# Session Security
SESSION_COOKIE_AGE = 3600
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# CSRF Security
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_AGE = 3600

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Production Security (when DEBUG=False)
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

#### Middleware Configuration
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "mainwebsite.security_middleware.SecurityHeadersMiddleware",
    "mainwebsite.security_middleware.CORSMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "mainwebsite.middleware.PasskeySessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

## Security Best Practices

### Development
1. **Never commit secrets**: Use environment variables for all sensitive data
2. **Test security features**: Run security tests regularly
3. **Keep dependencies updated**: Regular security updates
4. **Code review**: Security-focused code reviews

### Production Deployment
1. **HTTPS Only**: Enforce HTTPS for all traffic
2. **Environment Variables**: Use secure environment variable management
3. **Database Security**: Encrypted connections and proper access controls
4. **Monitoring**: Implement security monitoring and alerting
5. **Backups**: Regular encrypted backups

### Monitoring and Alerting
1. **Failed Authentication**: Monitor for brute force patterns
2. **Magic Link Abuse**: Track unusual magic link request patterns
3. **Session Anomalies**: Monitor for session hijacking attempts
4. **Input Validation Failures**: Track potential injection attempts

## Security Testing

### Test Coverage
- **92 Total Tests**: Comprehensive security test suite
- **Authentication Tests**: Passkey and magic link flows
- **Security Tests**: Headers, CORS, input validation
- **Integration Tests**: End-to-end security scenarios

### Running Security Tests
```bash
# Run all tests
python manage.py test

# Run specific security test suites
python manage.py test mainwebsite.test_security_headers
python manage.py test mainwebsite.test_input_validation

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pre-commit install

# Run all hooks
pre-commit run --all-files
```

## Incident Response

### Security Incident Checklist
1. **Identify**: Determine the scope and nature of the incident
2. **Contain**: Implement immediate containment measures
3. **Investigate**: Analyze logs and determine root cause
4. **Remediate**: Apply fixes and security patches
5. **Monitor**: Enhanced monitoring post-incident
6. **Document**: Update security procedures and documentation

### Emergency Contacts
- **System Administrator**: [Contact Information]
- **Security Team**: [Contact Information]
- **Development Team**: [Contact Information]

## Compliance

### Standards Compliance
- **OWASP Top 10**: Protection against common web vulnerabilities
- **WebAuthn Specification**: Full compliance with FIDO2/WebAuthn standards
- **Django Security**: Follows Django security best practices
- **NIST Framework**: Aligned with cybersecurity framework guidelines

### Security Certifications
- Regular security audits recommended
- Penetration testing for production deployments
- Compliance assessments as required

## Updates and Maintenance

### Security Updates
- **Monthly**: Review and apply security patches
- **Quarterly**: Security configuration review
- **Annually**: Comprehensive security audit
- **As Needed**: Emergency security updates

### Documentation Maintenance
- Keep security documentation current
- Update procedures after security incidents
- Regular review of security policies

---

For questions about security features or to report security issues, please contact the development team through secure channels.
