def clear_session_keys(session, *keys):
    try:
        for key in keys:
            del session[key]
        session.save()
    
    except Exception as e:
        return False
    return True
