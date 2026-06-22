import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from passkeys.models import UserPasskey

from mainwebsite import models
from mainwebsite.account_lockout import (
    clear_login_attempts,
    is_account_locked,
    record_failed_login,
)
from mainwebsite.decorators import passkey_login_required
from mainwebsite.input_validation import (
    get_safe_redirect_url,
    get_whitelisted_redirect_url,
    validate_url_input,
    validate_username_input,
)
from mainwebsite.magic_link_tokens import magic_link_token_generator
from mainwebsite.rate_limiting import (
    get_client_ip,
    get_user_agent,
    magic_link_rate_limiter,
)
from mainwebsite.site_content import homepage_content_context

from .forms import UsernameForm

logger = logging.getLogger(__name__)


def page_not_found_view(request, exception):
    return render(request, "404.html", status=404)


def homepage(request):
    context = {
        "title": "Home",
        "page_title": "Home",
        "meta_description": (
            "Atilano Garcia, a software engineer in Austin, TX. I build full-stack web "
            "apps for a living and side projects for the fun of it."
        ),
    }
    context.update(homepage_content_context())
    return render(request, "homepage.html", context)


def graduation(request):
    context = {
        "title": "Graduation",
        "content": "graduation",
        "page_title": "Graduation",
        "meta_description": "View Atilano Garcia's graduation photos and memories from university. Celebrating academic achievements and milestones in software engineering education.",
        "meta_keywords": "Atilano Garcia, graduation, university, academic achievements, software engineering education, college",
    }
    return render(request, "graduation.html", context)


def cube_wallpaper(request):
    context = {
        "title": "Cube Wallpaper",
        "page_title": "3D Cube Wallpaper Generator",
        "meta_description": "Interactive 3D cube wallpaper generator created by Atilano Garcia. Generate custom geometric wallpapers with dynamic cube animations and patterns.",
        "meta_keywords": "3D cube wallpaper, wallpaper generator, geometric patterns, interactive design, web graphics, CSS animations",
    }
    return render(request, "cube_wallpaper.html", context)


def resume(request):
    context = {
        "title": "Résumé",
        "page_title": "Résumé",
        "meta_description": (
            "Résumé of Atilano (Tilo) Garcia, Software Engineer II at Indeed in Austin, "
            "TX. Experience in full-stack web apps, AWS, data pipelines, and product "
            "launches."
        ),
    }
    return render(request, "resume.html", context)


def linkedin(request):
    return redirect("https://www.linkedin.com/in/atilano-garcia/")


def calendar_webpage(request):
    return render(request, "calendar.html")


def kky_acceptance_page(request):
    return render(request, "kky.html")


def url_shortener(request):
    context = {
        "page_title": "URL Shortener",
        "meta_description": (
            "URL shortener by Atilano Garcia. Turn a long link into a short, shareable "
            "redirect."
        ),
    }
    return render(request, "url_shortener.html", context)


def url_shortener_submit(request):
    if request.method == "POST":
        url = request.POST.get("url", "").strip()
        if url:
            # Validate the URL using our security-focused validation
            is_valid, error_message = validate_url_input(url)

            if is_valid:
                shortened_url = models.ShortenedUrl(real_url=url)
                shortened_url.save()
                return JsonResponse(
                    {
                        "shortened_url": f"{get_current_site(request)}/r/{shortened_url.shortened_url}"
                    }
                )
            else:
                return JsonResponse({"error": error_message}, status=400)
        else:
            return JsonResponse({"error": "URL is required"}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=405)


def redirect_url(request, shortened_url):
    possible_url = models.ShortenedUrl.objects.filter(shortened_url=shortened_url)
    if possible_url.exists():
        return redirect(possible_url.first().real_url)


def translator(request):
    context = {
        "title": "Translator",
        "page_title": "Translator",
        "meta_description": (
            "Two-way phone translator by Atilano Garcia. Bridge a live, translated call "
            "between two people who don't share a language."
        ),
    }
    return render(request, "translator.html", context)


@login_required
def passkey_register(request):
    """View for setting up a new passkey (requires user to be logged in via magic link)"""
    # Check if user accessed this page via magic link verification
    if not request.session.get("magic_link_verified", False):
        # User did not come via magic link - redirect to login
        messages.error(
            request, "Access to passkey registration requires magic link verification."
        )
        return redirect("mainwebsite:login")

    # Clear the flag after successful access to prevent reuse
    request.session.pop("magic_link_verified", None)

    return render(request, "passkey_register.html")


def get_domain_email(request):
    """Get the appropriate FROM email address based on the current domain"""
    domain = request.get_host().split(":")[0]  # Remove port if present

    # Map domains to email addresses
    domain_emails = {
        "atilanogarcia.com": "noreply@atilanogarcia.com",
        "www.atilanogarcia.com": "noreply@atilanogarcia.com",
        "tilogarcia.com": "noreply@tilogarcia.com",
        "www.tilogarcia.com": "noreply@tilogarcia.com",
        "tilog.me": "noreply@tilog.me",
        "www.tilog.me": "noreply@tilog.me",
    }

    # Return domain-specific email or fall back to default
    return domain_emails.get(domain, settings.DEFAULT_FROM_EMAIL)


class UnifiedLoginView(View):
    template_name = "unified_login.html"

    def get(self, request):
        form = UsernameForm()
        # Validate and sanitize the next parameter
        next_url = get_safe_redirect_url(
            request.GET.get("next", "/"), default_url="/", request=request
        )
        return render(
            request,
            self.template_name,
            {"form": form, "next": next_url},
        )

    def post(self, request):
        form = UsernameForm(request.POST)
        # Validate and sanitize the next parameter from both POST and GET
        raw_next = request.POST.get("next", request.GET.get("next", "/"))
        next_url = get_safe_redirect_url(raw_next, default_url="/", request=request)
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

        if form.is_valid():
            username = form.cleaned_data["username"]
            # Validate username input
            is_valid, error_msg = validate_username_input(username)
            if not is_valid:
                message = error_msg or "Invalid username format."
                if is_ajax:
                    return JsonResponse(
                        {"action": "error", "message": message}, status=400
                    )
                form.add_error(None, message)
                return render(
                    request, self.template_name, {"form": form, "next": next_url}
                )

            if is_account_locked(username=username, request=request):
                message = "Account is locked due to excessive failed login attempts."
                if is_ajax:
                    return JsonResponse(
                        {"action": "error", "message": message}, status=403
                    )
                form.add_error(None, message)
                return render(
                    request, self.template_name, {"form": form, "next": next_url}
                )

            try:
                user = User.objects.get(username=username)
                # Check if user has any passkeys
                has_passkey = UserPasskey.objects.filter(user=user).exists()

                if has_passkey:
                    # Store username and next URL in session for passkey auth
                    request.session["webauthn_username"] = username
                    request.session["next"] = next_url

                    if is_ajax:
                        return JsonResponse({"action": "prompt_passkey"})
                    else:
                        # For non-AJAX requests, show passkey UI on the same page
                        return render(
                            request,
                            self.template_name,
                            {
                                "form": form,
                                "next": next_url,
                                "show_passkey_ui": True,
                                "username": username,
                            },
                        )
                else:
                    # User doesn't have passkey, send magic link
                    try:
                        # For users without a passkey, the next step after magic
                        # link verification is always to register a passkey.
                        request.session["next"] = reverse(
                            "mainwebsite:passkey_register"
                        )
                        self.send_magic_link(request, user)

                        message = f"A secure magic link has been sent to your email address. It will expire in {magic_link_token_generator.get_token_expiration_minutes()} minutes."
                        if is_ajax:
                            return JsonResponse(
                                {"action": "magic_link_sent", "message": message}
                            )
                        else:
                            messages.success(request, message)
                            return render(
                                request,
                                self.template_name,
                                {"form": form, "next": next_url},
                            )
                    except Exception as e:
                        logger.error(f"Failed to send magic link: {e}")
                        error_message = "Failed to send magic link. Please try again."
                        if is_ajax:
                            return JsonResponse(
                                {"action": "error", "message": error_message},
                                status=500,
                            )
                        form.add_error(None, error_message)
                        return render(
                            request,
                            self.template_name,
                            {"form": form, "next": next_url},
                        )

            except User.DoesNotExist:
                record_failed_login(username=username, request=request)
                message = "User not found. Please check your username."
                if is_ajax:
                    return JsonResponse(
                        {"action": "error", "message": message}, status=400
                    )
                form.add_error(None, message)

        if is_ajax:
            return JsonResponse(
                {"action": "error", "message": "Invalid username."}, status=400
            )
        return render(request, self.template_name, {"form": form, "next": next_url})

    def send_magic_link(self, request, user):
        # Get client info for rate limiting and logging
        client_ip = get_client_ip(request)
        user_agent = get_user_agent(request)

        # Check rate limiting
        is_limited, reason, retry_after = magic_link_rate_limiter.is_rate_limited(
            user, client_ip
        )
        if is_limited:
            logger.warning(
                f"Magic link rate limited: user={user.username}, ip={client_ip}, reason={reason}"
            )
            # Record failed attempt
            magic_link_rate_limiter.record_request(
                user, user.email, client_ip, user_agent, success=False
            )
            raise Exception(reason)  # This will be caught by the calling code

        # Generate secure token
        token = magic_link_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        current_site = get_current_site(request)

        # Determine protocol (enforce HTTPS in production)
        protocol = (
            "https"
            if getattr(settings, "MAGIC_LINK_FORCE_HTTPS", False)
            else request.scheme
        )

        # Create magic link
        magic_link = f"{protocol}://{current_site.domain}{reverse('mainwebsite:magic_link_verify', kwargs={'uidb64': uid, 'token': token})}"

        # Get expiration time for user communication
        expiration_minutes = magic_link_token_generator.get_token_expiration_minutes()

        # Enhanced email content with security information
        mail_subject = "Secure Login Link - Expires in 15 Minutes"
        message = f"""Hello {user.username},

Click the link below to securely log in to your account:
{magic_link}

⚠️ SECURITY NOTICE:
• This link expires in {expiration_minutes} minutes for your security
• Only use this link if you requested it
• Never share this link with others
• If you didn't request this, please ignore this email

After logging in, you'll be able to set up a passkey for even more secure, passwordless authentication in the future.

Best regards,
The Security Team"""

        from_email = get_domain_email(request)

        try:
            send_mail(mail_subject, message, from_email, [user.email])

            # Record successful request
            magic_link_rate_limiter.record_request(
                user, user.email, client_ip, user_agent, success=True
            )

            logger.info(
                f"Magic link sent successfully: user={user.username}, email={user.email}, ip={client_ip}"
            )
        except Exception as e:
            # Record failed request
            magic_link_rate_limiter.record_request(
                user, user.email, client_ip, user_agent, success=False
            )
            logger.error(f"Failed to send magic link: user={user.username}, error={e}")
            raise


class MagicLinkVerifyView(View):
    def get(self, request, uidb64, token):
        # Get client info for logging
        client_ip = get_client_ip(request)
        get_user_agent(request)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
            logger.warning(
                f"Magic link verification failed - invalid user ID: uidb64={uidb64}, ip={client_ip}"
            )

        # Check if account is locked before proceeding
        if user and is_account_locked(username=user.username, request=request):
            logger.warning(
                f"Magic link verification blocked - account locked: user={user.username}, ip={client_ip}"
            )
            return render(
                request,
                "magic_link_invalid.html",
                {
                    "error_message": "Account is locked due to excessive failed attempts."
                },
            )

        if user is not None and magic_link_token_generator.check_token(user, token):
            # Successful magic link verification
            login(request, user)

            # Clear any failed login attempts after successful verification
            clear_login_attempts(username=user.username, request=request)

            logger.info(
                f"Magic link verification successful: user={user.username}, ip={client_ip}"
            )

            # Set session flag to indicate magic link verification
            request.session["magic_link_verified"] = True

            # Get the next URL from session with secure validation
            raw_next = request.session.pop(
                "next", reverse("mainwebsite:passkey_register")
            )

            # Use whitelist validation for magic link redirects
            allowed_urls = [
                "/",
                "/personal-ai/",
                "/passkeys-register/",
                reverse("mainwebsite:passkey_register"),
                reverse("mainwebsite:personal_ai"),
            ]
            next_url = get_whitelisted_redirect_url(
                raw_next,
                allowed_urls=allowed_urls,
                default_url=reverse("mainwebsite:passkey_register"),
            )

            # Redirect to the intended destination or passkey registration page
            return redirect(next_url)
        else:
            # Failed verification - log the attempt
            if user:
                logger.warning(
                    f"Magic link verification failed - invalid/expired token: user={user.username}, ip={client_ip}"
                )
            else:
                logger.warning(
                    f"Magic link verification failed - user not found: uidb64={uidb64}, ip={client_ip}"
                )

            return render(request, "magic_link_invalid.html")


@passkey_login_required
def personal_ai(request):
    """Renders the personal AI page, which is accessible after login."""
    return render(request, "personal_ai.html")


def custom_logout(request):
    """Custom logout view that clears passkey authentication session flag"""
    # Clear the passkey authentication flag from session
    if "passkey_authenticated" in request.session:
        del request.session["passkey_authenticated"]

    # Clear the passkey session timestamp
    if "passkey_last_activity" in request.session:
        del request.session["passkey_last_activity"]

    # Clear any remaining WebAuthn session data
    if "webauthn_username" in request.session:
        del request.session["webauthn_username"]

    # Perform standard logout
    logout(request)

    # Redirect to the unified login page
    return redirect(reverse("mainwebsite:login"))


def intro(request):
    """Intro page with Rick Roll video from Cloudflare R2"""
    context = {
        "title": "Introduction",
        "page_title": "Introduction",
        "meta_description": "Welcome to Atilano Garcia's introduction page",
        "video_url": "https://content.atilanogarcia.com/Rick%20Roll.mp4",
    }
    return render(request, "intro.html", context)
