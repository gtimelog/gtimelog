# The gtimelog package.

__version__ = '0.9.2.dev0'

# A simplistic hook mechanism. Extensions should do this:
#   import gtimelog
#   gtimelog.hooks['ui'].append(extend_ui)
# The code that provides the hook then calls each function in the list for
# the 'ui' hook.
#
# The function signature for each hook's callback is different. See below.
hooks = {
    # Callback: foo(mw, builder, resource_dir), where mw is the MainWindow
    # instance, buider is the GtkBuilder object used to load UI files, and
    # resource_dir is where ther UI files should be stored. Callback will
    # be called before signals are connected.
    'ui': [],

    # Callback: foo(). Called before the GTK main loop starts.
    'before-gtk-main': [],

    # Callback: foo(). Called after the GTK main loop ends.
    'after-gtk-main': [],
}

def call_hook(name, *args, **kwargs):
    '''Call every hook callback (or until first one that returns non-None).'''
    for func in hooks[name]:
        ret = func(*args, **kwargs)
        if ret is not None:
            return ret
