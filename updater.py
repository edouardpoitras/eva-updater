import os
import sys
import shutil
import datetime
import gossip
from git import Repo
from eva.plugin import get_plugin_directory, pull_repo
from eva.util import restart, get_mongo_client
from eva.plugin import plugin_enabled
from eva import log
from eva import conf
from eva import scheduler

UPDATE_CHECK_INTERVAL = conf['plugins']['updater']['config']['update_check_interval']
ROLLBACK_DIRECTORY = conf['plugins']['updater']['config']['rollback_directory']

UPDATED = 'Updated'
BEHIND = 'Behind'
UNKNOWN = 'Unknown'

client = get_mongo_client()

def on_enable():
    # Check for rollback flag
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        rollback()

def rollback_available():
    return os.path.isdir(ROLLBACK_DIRECTORY) and os.listdir(ROLLBACK_DIRECTORY)

def rollback(reboot=True):
    log.warning('User initiated rollback process')
    if not rollback_available():
        log.error('Failed to rollback - rollback directory is empty or does not exist: %s' %ROLLBACK_DIRECTORY)
        return
    plugin_dir = get_plugin_directory()
    if os.path.isdir(plugin_dir):
        shutil.rmtree(plugin_dir)
    shutil.move(ROLLBACK_DIRECTORY, plugin_dir)
    log.info('Rollback complete')
    if reboot: restart()

def backup():
    log.info('Creating backup of plugins directory')
    plugin_dir = get_plugin_directory()
    shutil.copytree(plugin_dir, ROLLBACK_DIRECTORY)

@scheduler.scheduled_job('interval', hours=UPDATE_CHECK_INTERVAL, id='eva_updater')
def update_check():
    log.info('Update check initiated')
    update_data = []
    for p in conf['plugins']:
        log.debug('Checking %s for updates...' %p)
        plugin = conf['plugins'][p]
        if plugin['git']:
            log.debug('Found git repo: %s' %p)
            repo = Repo(plugin['path'])
            origin = repo.remotes.origin
            origin.fetch()
            commits_behind = repo.iter_commits('master..origin/master')
            count = sum(1 for c in commits_behind)
            if count > 0:
                log.info('%s is behind' %p)
                state = BEHIND
            else:
                log.info('%s is up-to-date' %p)
                state = UPDATED
            update_data.append({'name': p, 'state': state, 'type': 'git'})
        else:
            log.info('%s has no git repo' %p)
            update_data.append({'name': p, 'state': UNKNOWN, 'type': None})
    collection = client.eva.updates
    # Delete entries in updates collection.
    collection.delete_many({})
    # Store plugins update information in DB.
    collection.insert(update_data)
    log.info('Update check complete')

def get_state(plugin_id):
    collection = client.eva.updates
    data = collection.find_one({'name': plugin_id})
    if data is None or not 'state' in data: return UNKNOWN
    return data['state']

def set_state(plugin_id, state):
    collection = client.eva.updates
    collection.find_one_and_update({'name': plugin_id}, {'$set': {'state': UPDATED}})

def is_behind(plugin_id):
    return get_state(plugin_id) == BEHIND

def is_updated(plugin_id):
    return get_state(plugin_id) == UPDATED

def is_unknown(plugin_id):
    return get_state(plugin_id) == UNKNOWN

def update_plugin(plugin_id, save_backup=True):
    """
    Assumes latest plugin version is in master branch.
    """
    log.info('Updating plugin: %s' %plugin_id)
    plugin = conf['plugins'][plugin_id]
    # Ensure plugin has a git repo.
    if not plugin['git']:
        log.warning('Can not update plugin %s: not a git repo' %plugin_id)
        return
    plugin_dir = get_plugin_directory()
    # Ensure plugin exists in plugin directory.
    if not os.path.isdir(plugin_dir + '/' + plugin_id):
        log.error('Plugin %s not found in plugin directory: %s' %(plugin_id, plugin_dir))
        return
    if save_backup:
        # Delete old rollback directory.
        if rollback_available():
            log.info('Removing existing rollback directory')
            shutil.rmtree(ROLLBACK_DIRECTORY)
        backup()
    pull_repo(plugin['path'])
    set_state(plugin_id, UPDATED)
    log.info('Plugin updated: %s' %plugin_id)

def update_all_plugins(save_backup=True, disabled=False, reboot=False):
    log.info('Updating all plugins')
    if save_backup:
        # Delete old rollback directory.
        if rollback_available():
            log.info('Removing existing rollback directory')
            shutil.rmtree(ROLLBACK_DIRECTORY)
        backup()
    for plugin_id in conf['plugins']:
        if not plugin_enabled(plugin_id) and not disabled:
            log.info('Skipping disabled plugin: %s' %plugin_id)
            continue
        update_plugin(plugin_id, save_backup=False)
    log.info('All plugins updated')
    if reboot: restart()
