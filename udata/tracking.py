def send_signal(signal, request, user, **kwargs):
    """Generic method to send signals to Piwik

    given that we always have to compute IP and UID for instance.
    """
    params = {"user_ip": request.remote_addr}
    params.update(kwargs)
    if user.is_authenticated:
        params["uid"] = user.id
    signal.send(request.url, **params)
