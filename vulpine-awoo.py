#!/usr/bin/env python3
import configparser
import getpass

CONFIG_FILE = None
TIMELINE = "tag/VulpineClubBulletin"


def read_app_credentials(filename="app_credentials.cfg"):
    creds = configparser.RawConfigParser()
    creds.read(filename)
    return creds


def read_config_file(filename=None):
    """Read and parse the configuration file, returning it as a ConfigParser
       object."""
    global CONFIG_FILE

    config = configparser.RawConfigParser()

    if filename is None:
        filename = CONFIG_FILE

    config.read(filename)
    CONFIG_FILE = filename

    return config


def write_config_file(config):
    """Writes the configuration object to the previously-read config file."""
    global CONFIG_FILE

    if CONFIG_FILE is None:
        raise RuntimeError('CONFIG_FILE is None')

    with open(CONFIG_FILE, 'w') as fp:
        config.write(fp)


def get_mastodon(credentials, config):
    """Returns a Mastodon connection object."""
    from mastodon import Mastodon

    if not credentials.has_section('mastodon'):
        raise RuntimeError("no [mastodon] section in app credentials")

    for key in ['client_key', 'client_secret', 'instance']:
        if not credentials.has_option('mastodon', key):
            raise RuntimeError("no %s key in app credentials" % key)

    if not config.has_section('mastodon'):
        config.add_section('mastodon')
        write_config_file(config)

    # Log in
    if not config.has_option('mastodon', 'access_token'):
        mastodon = Mastodon(
                    client_id=credentials.get('mastodon', 'client_key'),
                    client_secret=credentials.get('mastodon', 'client_secret'),
                    api_base_url=credentials.get('mastodon', 'instance'))
        print(("Logging into %s..." % credentials.get('mastodon', 'instance')))
        username = input('E-mail address: ')
        password = getpass.getpass('Password: ')
        access_token = mastodon.log_in(username, password)
        config.set('mastodon', 'access_token', access_token)
        write_config_file(config)

    return Mastodon(
            client_id=credentials.get('mastodon', 'client_key'),
            client_secret=credentials.get('mastodon', 'client_secret'),
            api_base_url=credentials.get('mastodon', 'instance'),
            access_token=config.get('mastodon', 'access_token'))


def set_tag_high_water_mark(config, last):
    """Set the marker for the latest last.fm track processed."""
    if not config.has_section('tag'):
        config.add_section('tag')

    config.set('tag', 'last_timestamp', last)
    write_config_file(config)


def get_tag_high_water_mark(config):
    """Get the marker for the latest last.fm track processed."""
    if (not config.has_section('tag') or
            not config.has_option('tag', 'last_timestamp')):
        return 1

    return config.getint('tag', 'last_timestamp')


def is_boostworthy(mastodon, post):
    relations = mastodon.account_relationships(post.account.id)
    for r in relations:
        if r.id == post.account.id and r.following and not post.reblogged:
            return True
    return False


def main():
    creds = read_app_credentials()
    cfg = read_config_file('config.cfg')

    mastodon = get_mastodon(creds, cfg)

    hwm = get_tag_high_water_mark(cfg)

    for sr in mastodon.timeline(TIMELINE, since_id=hwm):
        hwm = sr.id
        if is_boostworthy(mastodon, sr):
            mastodon.status_reblog(sr.id)

    set_tag_high_water_mark(cfg, hwm)


if __name__ == '__main__':
    main()
