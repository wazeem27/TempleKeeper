# middleware.py
from django.utils.deprecation import MiddlewareMixin
from temple_auth.models import Temple


class SelectedTempleMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if 'selected_temple_id' in request.session:
            try:
                request.selected_temple = Temple.objects.get(id=request.session['selected_temple_id'])
            except Temple.DoesNotExist:
                request.selected_temple = None
        else:
            request.selected_temple = None