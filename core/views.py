from django.views.generic import TemplateView, ListView
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
import json

from newsfeed.models import FeedItem, FeedItemManager
from church.models import Member, Branch, DiscipleshipEnrollment
from gym.models import SchoolDisciple

User = get_user_model()


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


@require_POST
def ai_assistant_reply(request):
    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"reply": "Sorry, I didn't understand that."}, status=400)

    raw_msg = data.get("message") if isinstance(data, dict) else None
    user_msg = (raw_msg or "").lower().strip()[:500] if isinstance(raw_msg, str) else ""

    faq = {
        "sunday": "Sunday services run from 9:00 AM to 10:00 PM every Sunday.",
        "service time": "Sunday services run from 9:00 AM to 10:00 PM every Sunday.",
        "discipleship": "Discipleship classes run every Saturday 7:00 AM-12:00 PM and Sunday 12:00 PM-4:00 PM, in 3-month phases.",
        "membership": "You can register as a member through the church office, or ask an usher to connect you with our Membership Admin.",
        "aff": "Apostles' Feet Foundation supports members facing financial hardship. Speak to the AFF office for an assistance form.",
        "live": "Check the Live section from the main menu to see if a service is currently streaming.",
        "location": "Please check the Contact page for our branch locations.",
    }

    reply = "Thanks for reaching out! An admin will get back to you shortly. Meanwhile, try asking about service times, discipleship, membership, or AFF."
    for key, answer in faq.items():
        if key in user_msg:
            reply = answer
            break

    return JsonResponse({"reply": reply})