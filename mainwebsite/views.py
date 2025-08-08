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
from mainwebsite.decorators import passkey_login_required
from mainwebsite.magic_link_tokens import magic_link_token_generator
from mainwebsite.rate_limiting import (
    get_client_ip,
    get_user_agent,
    magic_link_rate_limiter,
)

from .forms import UsernameForm

logger = logging.getLogger(__name__)


def page_not_found_view(request, exception):
    return render(request, "404.html", status=404)


def homepage(request):
    context = {"title": "Home Page", "content": "homepage"}
    return render(request, "homepage.html", context)


def graduation(request):
    context = {"title": "Graduation", "content": "graduation"}
    return render(request, "graduation.html", context)


def cube_wallpaper(request):
    context = {
        "title": "Cube Wallpaper",
    }
    return render(request, "cube_wallpaper.html", context)


def resume(request):
    context = {"title": "Resume", "content": "resume"}
    return render(request, "base.html", context)


def linkedin(request):
    return redirect("https://www.linkedin.com/in/atilano-garcia/")


def calendar_webpage(request):
    return render(request, "calendar.html")


def kky_acceptance_page(request):
    context = {}
    return render(request, "kky.html", context)


def url_shortener(request):
    return render(request, "url_shortener.html")


def url_shortener_submit(request):
    if request.method == "POST":
        url = request.POST["url"]
        if url:
            shortened_url = models.ShortenedUrl(real_url=url)
            shortened_url.save()
            return JsonResponse(
                {
                    "shortened_url": f"{get_current_site(request)}/r/{shortened_url.shortened_url}"
                }
            )
    return JsonResponse({})


def redirect_url(request, shortened_url):
    possible_url = models.ShortenedUrl.objects.filter(shortened_url=shortened_url)
    if possible_url.exists():
        return redirect(possible_url.first().real_url)


def translator(request):
    context = {"title": "Translator", "content": "translator"}
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
        return render(
            request,
            self.template_name,
            {"form": form, "next": request.GET.get("next", "/")},
        )

    def post(self, request):
        form = UsernameForm(request.POST)
        next_url = request.POST.get("next", request.GET.get("next", "/"))
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

        if form.is_valid():
            username = form.cleaned_data["username"]
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
                    # For non-AJAX requests, stay on login page to show passkey UI
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
                    # User doesn't have a passkey, send magic link
                    try:
                        self.send_magic_link(request, user)
                        message = "A secure magic link has been sent to your email address. It will expire in 15 minutes."
                    except Exception as e:
                        # Handle rate limiting and other errors
                        error_message = str(e)
                        if (
                            "rate limited" in error_message.lower()
                            or "too many" in error_message.lower()
                        ):
                            message = error_message
                        else:
                            message = (
                                "Unable to send magic link. Please try again later."
                            )
                            logger.error(
                                f"Magic link send error for user {username}: {e}"
                            )

                    if is_ajax:
                        return JsonResponse(
                            {"action": "magic_link_sent", "message": message}
                        )
                    messages.success(request, message)
                    return render(
                        request, self.template_name, {"form": form, "next": next_url}
                    )

            except User.DoesNotExist:
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

        if user is not None and magic_link_token_generator.check_token(user, token):
            # Successful magic link verification
            login(request, user)

            logger.info(
                f"Magic link verification successful: user={user.username}, ip={client_ip}"
            )

            # Set session flag to indicate magic link verification
            request.session["magic_link_verified"] = True

            # Get the next URL from session or default to passkey registration
            next_url = request.session.pop(
                "next", reverse("mainwebsite:passkey_register")
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
