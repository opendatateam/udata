from blinker import Namespace

namespace = Namespace()

#: Triggered when a spam is detected
on_new_potential_spam = namespace.signal('on-new-potential-spam')
