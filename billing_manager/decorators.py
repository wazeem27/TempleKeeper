from django.shortcuts import redirect



def check_temple_session(func):
    def wrapper(request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        if not temple_id:
            return redirect('temple_selection')
        return func(request, *args, **kwargs)
    return wrapper