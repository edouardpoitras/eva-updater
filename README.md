Updater
=======

An Eva plugin that facilitates updating Eva plugins.

## Installation

Can be easily installed through the Web UI by using [Web UI Plugins](https://github.com/edouardpoitras/eva-web-ui-plugins).

Alternatively, add `updater` to your `eva.conf` file in the `enabled_plugins` option list and restart Eva.

## Usage

Once enabled, a new periodic job will check for Eva plugin updates.

Plugin update status will be stored in a MongoDB collection named `updates`.

This plugin exposes many helper functions used when updating plugins (see the Developer section).
Most often used with the [Web UI Updater](https://github.com/edouardpoitras/eva-web-ui-updater) plugin in order to update plugins through the Web UI.

You can start Eva with the --rollback flag in order to undo the last applied update (can only be performed once for every update - no multiple undos are supported as of version 0.1.0).

## Developers

The following functions are made available by this plugin (see source code for more details):

```python
update_all_plugins(save_backup=True, disabled=False, reboot=False) # Updates all plugins.
update_plugin(plugin_name, save_backup=True) # Update a single plugin.
is_unknown(plugin_id) # Check if a plugin is in 'Unknown' state.
is_updated(plugin_id) # Check if a plugin is in 'Updated' state.
is_behind(plugin_id) # Check if a plugin is in 'Behind' state.
set_state(plugin_id, state) # Sets the state of plugin.
get_state(plugin_id) # Gets the state of a plugin.
update_check() # What runs periodically to check for updates.
backup() # Backs up the entire plugin directory to the configured rollback directory.
rollback(reboot=True) # Performs the rollback.
rollback_available() # Checks if a rollback is available.
```

Available plugin states are defined as follows:

```python
UPDATED = 'Updated'
BEHIND = 'Behind'
UNKNOWN = 'Unknown'
```

## Configuration

Default configurations can be changed by adding a `updater.conf` file in your plugin configuration path (can be configured in `eva.conf`, but usually `~/eva/configs`).

To get an idea of what configuration options are available, you can take a look at the `updater.conf.spec` file in this repository, or use the [Web UI Plugins](https://github.com/edouardpoitras/eva-web-ui-plugins) plugin and view them at `/plugins/configuration/updater`.

Here is a breakdown of the available options:

    rollback_directory
        Type: String
        Default: '/tmp/eva_rollback'
        The directory to use for rollbacks (backups).
    update_check_interval
        Type: Integer
        Default: 24
        How frequently (in hours) to check for updates.
        Effectively, the number of hours in between each update_check() job run.
