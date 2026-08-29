from django.views.generic import TemplateView, ListView
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.utils import OperationalError
import json
import re

from django_ratelimit.decorators import ratelimit

from newsfeed.models import FeedItem, FeedItemManager
from church.models import Member, Branch, DiscipleshipEnrollment, LiveService, PastorElder
from gym.models import SchoolDisciple, School
from .models import SiteContact

User = get_user_model()


@require_GET
def health_check(request):
    """For uptime monitors / load balancer health checks — unauthenticated,
    unrate-limited, and does a real DB round trip rather than just returning 200."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except OperationalError:
        return JsonResponse({'status': 'error', 'database': 'unreachable'}, status=503)
    return JsonResponse({'status': 'ok'})


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['feed_items'] = list(FeedItemManager.active()[:30])
        ctx['live_item'] = FeedItemManager.active().filter(item_type=FeedItem.ItemType.LIVE).first()
        ctx['member_count'] = Member.objects.filter(is_active=True).count()
        ctx['branch_count'] = Branch.objects.filter(is_active=True).count()
        ctx['worker_count'] = User.objects.filter(is_active=True).exclude(role=User.Role.MEMBER).count()
        ctx['disciple_count'] = (
            DiscipleshipEnrollment.objects.filter(status='ongoing').count()
            + SchoolDisciple.objects.count()
        )
        return ctx


class PortalLoginView(LoginView):
    template_name = "core/portal_login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        if user.two_factor_enabled:
            self.request.session['2fa_user_id'] = user.pk
            self.request.session['2fa_next'] = self.get_success_url()
            return redirect('accounts:two_factor_verify')
        return super().form_valid(form)


class SearchView(ListView):
    model = FeedItem
    template_name = "core/search_results.html"
    context_object_name = "results"

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        if not query:
            return FeedItem.objects.none()
        return FeedItemManager.active().filter(title__icontains=query)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['query'] = self.request.GET.get('q', '')
        return ctx


class AboutOverviewView(TemplateView):
    template_name = "core/about_overview.html"


class ContactView(TemplateView):
    template_name = "core/contact.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['contact'] = SiteContact.objects.first()
        return ctx


class PrivacyPolicyView(TemplateView):
    template_name = "core/privacy_policy.html"


def _live_status_answer():
    service = LiveService.objects.filter(is_live=True).first()
    if service:
        return (
            f'Yes, we\'re live right now on {service.get_platform_display()}: '
            f'"{service.title}" — head to the Live page to watch.'
        )
    return "We're not live right now. Sunday services run 9:00 AM-10:00 PM — check the Live page once service starts."


def _branches_answer():
    branches = list(Branch.objects.filter(is_active=True).values_list('name', 'location'))
    if not branches:
        return "Please check the Contact page for our branch locations."
    listed = "; ".join(f"{name} ({location})" for name, location in branches[:6])
    extra = "" if len(branches) <= 6 else f", and {len(branches) - 6} more"
    return f"Our branches: {listed}{extra}. See the Branches page for full details."


def _leadership_answer():
    leaders = list(
        PastorElder.objects.filter(is_active=True).order_by('display_order').values_list('full_name', flat=True)[:5]
    )
    if not leaders:
        return "Please check the Pastors & Elders page for our current leadership."
    return f"Our leadership team includes {', '.join(leaders)}. See the Pastors & Elders page for full bios."


def _gym_answer():
    count = School.objects.filter(is_active=True).count()
    if count:
        return (
            f"Global Youth Ministry (GYM) is active in {count} school{'' if count == 1 else 's'}, running "
            "discipleship, mentorship, and counselling programs for students. Visit the GYM page for more."
        )
    return "Global Youth Ministry (GYM) runs discipleship, mentorship, and counselling programs in schools. Visit the GYM page for more."


# Ordered (keywords, answer) rules — first whole-word/phrase match wins. `answer` is either a
# literal string, or a zero-argument callable for anything that should reflect live data.
FAQ_RULES = [
    (('hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening'),
     "Hello! I'm the ACC assistant. Ask me about service times, discipleship, membership, giving, GYM, or AFF, and I'll do my best to help."),
    (('thank you', 'thanks', 'thank u'),
     "You're very welcome! Let me know if there's anything else I can help with."),
    (('what can you do', 'who are you', 'what are you'),
     "I'm a simple assistant for Apostolic Campus Church — I can answer questions about service times, discipleship, membership, prayer requests, counseling, giving, GYM, and AFF."),
    (('live', 'streaming', 'watch online', 'watch live'), _live_status_answer),
    (('sunday', 'service time', 'what time is service', 'when is service'),
     "Sunday services run from 9:00 AM to 10:00 PM every Sunday."),
    (('discipleship', 'disciple'),
     "Discipleship classes run every Saturday 7:00 AM-12:00 PM and Sunday 12:00 PM-4:00 PM, in 3-month phases."),
    (('membership', 'become a member', 'join the church', 'how do i join'),
     "You can register as a member through the church office, or ask an usher to connect you with our Membership Admin."),
    (('prayer request', 'pray for me', 'prayer'),
     "You can submit a prayer request from the main menu — anonymously if you'd like. Our Membership team reviews every one."),
    (('counseling', 'counselling', 'counsel'),
     "Counseling sessions run Mondays and Wednesdays, 8:00 AM-4:00 PM, with the lead pastor. Book from the main menu."),
    (('give', 'giving', 'donate', 'donation', 'tithe', 'offering', 'mobile money', 'momo', 'bank account'),
     "You can give online — the Give page lists our bank and mobile money accounts, and lets you log what you sent so Finance can confirm it."),
    (('sermon', 'teaching', 'library', 'book'),
     "Check the Sermons, Teachings, and Library sections from the main menu — books can be read online or downloaded for free."),
    (('branch', 'location', 'where are you', 'address'), _branches_answer),
    (('pastor', 'elder', 'who leads', 'leadership'), _leadership_answer),
    (('gym', 'global youth ministry', 'school club'), _gym_answer),
    (("apostles' feet", 'apostles feet', 'aff', 'financial help', 'assistance', 'need help'),
     "Apostles' Feet Foundation supports members facing financial hardship. Speak to the AFF office, or ask a Membership Admin, for an assistance form."),
    (('contact', 'phone number', 'email', 'reach you'),
     "Please check the Contact page for our phone number, email, and branch addresses."),
]

DEFAULT_REPLY = (
    "Thanks for reaching out! An admin will get back to you shortly. "
    "Meanwhile, try asking about service times, discipleship, membership, giving, GYM, or AFF."
)


@require_POST
@ratelimit(key='ip', rate='30/m', block=True)
def ai_assistant_reply(request):
    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"reply": "Sorry, I didn't understand that."}, status=400)

    raw_msg = data.get("message") if isinstance(data, dict) else None
    user_msg = (raw_msg or "").lower().strip()[:500] if isinstance(raw_msg, str) else ""

    reply = DEFAULT_REPLY
    for keywords, answer in FAQ_RULES:
        if any(re.search(r'\b' + re.escape(keyword) + r'\b', user_msg) for keyword in keywords):
            reply = answer() if callable(answer) else answer
            break

    return JsonResponse({"reply": reply})