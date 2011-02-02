import re, urllib, hashlib

_wrapped_email=re.compile(r'.*<(.+)>')

def id(email):
    """Turn an email address into a Gravatar id as per <http://gravatar.com/site/implement/url>

    The supplied email address must be of the form 'Wolf@example.com',
    or else 'Wolf <wolf@example.com>'

    The result may be saved for use in later calls to gravatar.url().

    """
    match = _wrapped_email.match(email)
    if match:
        email = match.group(1)
    return hashlib.md5(email.strip().lower()).hexdigest()

def url(email=None, gravatar_id=None, **kw):
    """Build a complete gravatar URL with our favorite defaults.

    Keyword Arguments:

    email       -- (required if gravatar_id is None) a string containing
    an email address to be digested by gravatar.id(), above.

    gravatar_id -- (optional) the pre-digested id from which to build
    the URL, as generated by gravatar.id(), above.

    You must provide at least one of gravatar_id or email.  email will
    be ignored if both are supplied.  Remaining keyword arguments will
    be used to construct the URL itself.  Gravatar recognizes these
    three:

    's' or 'size'       -- size in pixels of the returned square image,
    Gravatar's default is 80x80

    'd' or 'default'    -- URL for a default image, or a keyword naming
    a Gravatar supplied default e.g., 'wavatar', 'identicon'.

    'r' or 'rating'     -- 'g', 'pg', 'r', or 'x' to refuse any "harder"
    rated image.  We default to 'pg'.

    Example:
        gravatar.url('Wolf@example.com', size=24)
    Result:
        "https://secure.gravatar.com/avatar/d3514940ac1b2051c8aa42970d17e3fe?size=24&r=pg&d=wavatar"

    Example:
        saved_id = gravatar.id('Wolf@example.com')
        url = gravatar.url(gravatar_id=saved_id, r='g')
    Result:
        "https://secure.gravatar.com/avatar/d3514940ac1b2051c8aa42970d17e3fe?r=g&d=wavatar"

    """
    assert gravatar_id or email
    if gravatar_id is None:
        gravatar_id = id(email)
    if 'r' not in kw and 'rating' not in kw: kw['r'] = 'pg'
    return ('https://secure.gravatar.com/avatar/%s?%s' % (gravatar_id, urllib.urlencode(kw)))

def for_user(user):
    return url(user.preferences['email_address'])
