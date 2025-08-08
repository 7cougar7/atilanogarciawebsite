import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
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
    """View for setting up a new passkey (requires user to be logged in)"""
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
        logger.error(f"UnifiedLoginView POST: Headers: {dict(request.headers)}")
        logger.error(f"UnifiedLoginView POST: Method: {request.method}")
        logger.error(f"UnifiedLoginView POST: Content-Type: {request.content_type}")
        logger.error(f"UnifiedLoginView POST: POST data: {dict(request.POST)}")

        form = UsernameForm(request.POST)
        next_url = request.POST.get("next", request.GET.get("next", "/"))
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

        logger.error(f"UnifiedLoginView POST: is_ajax={is_ajax}")
        logger.error(f"UnifiedLoginView POST: next_url={next_url}")
        logger.error(f"UnifiedLoginView POST: form.is_valid()={form.is_valid()}")

        if not form.is_valid():
            logger.error(f"UnifiedLoginView POST: form errors: {form.errors}")

        if form.is_valid():
            username = form.cleaned_data["username"]
            logger.error(f"UnifiedLoginView POST: username={username}")
            try:
                user = User.objects.get(username__iexact=username)
                logger.error(f"UnifiedLoginView POST: user found: {user.username}")
                if UserPasskey.objects.filter(user=user).exists():
                    logger.error(
                        "UnifiedLoginView POST: user has passkey, setting session and responding"
                    )
                    # User has a passkey, prompt for it
                    request.session["webauthn_username"] = user.username
                    request.session["next"] = next_url
                    if is_ajax:
                        logger.error(
                            "UnifiedLoginView POST: returning JSON response for passkey prompt"
                        )
                        return JsonResponse({"action": "prompt_passkey"})
                    logger.error(
                        "UnifiedLoginView POST: staying on login page for passkey authentication"
                    )
                    # Stay on the same login page but show passkey authentication UI
                    return render(
                        request,
                        self.template_name,
                        {"form": form, "next": next_url, "show_passkey": True},
                    )
                else:
                    logger.error(
                        "UnifiedLoginView POST: user has no passkey, sending magic link"
                    )
                    # User exists but has no passkey, send magic link
                    request.session["next"] = next_url
                    self.send_magic_link(request, user)
                    message = "Please check your email for a magic link to register your first passkey."
                    if is_ajax:
                        logger.error(
                            "UnifiedLoginView POST: returning JSON response for magic link"
                        )
                        return JsonResponse(
                            {"action": "magic_link_sent", "message": message}
                        )
                    messages.success(request, message)
                    return render(
                        request, self.template_name, {"form": form, "next": next_url}
                    )
            except User.DoesNotExist:
                logger.error(f"UnifiedLoginView POST: user not found: {username}")
                message = "No account found with that username."
                if is_ajax:
                    logger.error(
                        "UnifiedLoginView POST: returning JSON error for user not found"
                    )
                    return JsonResponse(
                        {"action": "error", "message": message}, status=400
                    )
                form.add_error(None, message)

        logger.error("UnifiedLoginView POST: form invalid or other error")
        if is_ajax:
            return JsonResponse(
                {"action": "error", "message": "Invalid username."}, status=400
            )
        return render(request, self.template_name, {"form": form, "next": next_url})

    def send_magic_link(self, request, user):
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        current_site = get_current_site(request)
        mail_subject = "Log in to your account"
        # This will point to a new view we will create next
        magic_link = f"http://{current_site.domain}{reverse('mainwebsite:magic_link_verify', kwargs={'uidb64': uid, 'token': token})}"
        message = f"Hello {user.username},\n\nClick the link below to log in and set up your passkey:\n{magic_link}"

        from_email = get_domain_email(request)
        send_mail(mail_subject, message, from_email, [user.email])


class MagicLinkVerifyView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            login(request, user)
            # Get the next URL from session or default to passkey registration
            next_url = request.session.pop(
                "next", reverse("mainwebsite:passkey_register")
            )
            # Redirect to the intended destination or passkey registration page
            return redirect(next_url)
        else:
            # We'll need a template for this
            return render(request, "magic_link_invalid.html")


@passkey_login_required
def personal_ai(request):
    """Renders the personal AI page, which is accessible after login."""
    return render(request, "personal_ai.html")
